import argparse
import csv
import re
from pathlib import Path

import yt_dlp

from services.enrichment.ingredient_resolution.ingredient_resolver import (
    IngredientResolver,
)
from services.enrichment.recipe_enricher import RecipeEnricher
from services.ingestion.raw_record import RawRecord
from services.pipeline.recipe_pipeline import RecipePipeline


YOUR_FOOD_LAB_CHANNEL_URL = (
    "https://www.youtube.com/channel/UCe2JAC5FUfbxLCfAvBWmNJA/videos"
)
DEFAULT_OUTPUT_DIR = Path("data/datasets/youtube/your_food_lab")
SOURCE_ID = "youtube.your_food_lab"


def clean_text(value):
    text = str(value or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def list_channel_videos(channel_url, max_videos):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": max_videos,
        "skip_download": True,
    }
    info = yt_dlp.YoutubeDL(opts).extract_info(channel_url, download=False)
    return list(info.get("entries") or [])


def fetch_video_info(video_id):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    return yt_dlp.YoutubeDL(opts).extract_info(url, download=False)


def parse_description_recipe(info):
    description = info.get("description") or ""
    ingredients_block = _between(
        description,
        [r"^Ingredients\s*:"],
        [r"^Method\s*:", r"^Process\s*:", r"^Directions\s*:"],
    )
    method_block = _after(
        description,
        [r"^Method\s*:", r"^Process\s*:", r"^Directions\s*:"],
    )

    if method_block:
        method_block = _before(
            method_block,
            [
                r"^#",
                r"^Follow ",
                r"^Intro\s+\d",
                r"^Outro\s+\d",
                r"^The Music I use",
            ],
        )

    ingredients = _ingredient_lines(ingredients_block)
    steps = _step_lines(method_block)

    if not ingredients or not steps:
        return None

    title = _written_recipe_title(description) or clean_text(info.get("title"))
    source_url = f"https://www.youtube.com/watch?v={info.get('id')}"

    return {
        "title": title,
        "description": clean_text(_intro_text(description)),
        "source_url": source_url,
        "ingredients": " | ".join(ingredients),
        "instructions": " | ".join(steps),
        "raw_text": clean_text(description),
        "youtube_video_id": info.get("id"),
        "youtube_channel": "Your Food Lab",
        "youtube_channel_url": YOUR_FOOD_LAB_CHANNEL_URL,
        "duration_seconds": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "view_count": info.get("view_count"),
    }


def _between(text, start_patterns, end_patterns):
    lines = str(text or "").splitlines()
    selected = []
    collecting = False

    for line in lines:
        stripped = line.strip()

        if not collecting and _matches(stripped, start_patterns):
            collecting = True
            continue

        if collecting and _matches(stripped, end_patterns):
            break

        if collecting:
            selected.append(line)

    return "\n".join(selected).strip()


def _after(text, start_patterns):
    lines = str(text or "").splitlines()
    selected = []
    collecting = False

    for line in lines:
        stripped = line.strip()

        if not collecting and _matches(stripped, start_patterns):
            collecting = True
            continue

        if collecting:
            selected.append(line)

    return "\n".join(selected).strip()


def _before(text, end_patterns):
    selected = []

    for line in str(text or "").splitlines():
        stripped = line.strip()

        if _matches(stripped, end_patterns):
            break

        selected.append(line)

    return "\n".join(selected).strip()


def _matches(line, patterns):
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)


def _ingredient_lines(block):
    lines = []
    quantity_words = (
        "cup",
        "cups",
        "tsp",
        "tbsp",
        "tablespoon",
        "teaspoon",
        "gram",
        "grams",
        "kg",
        "ml",
        "pinch",
        "handful",
        "required",
        "taste",
        "sized",
        "prepared",
    )

    for line in str(block or "").splitlines():
        line = clean_text(line)

        if not line:
            continue

        lower = line.lower()
        has_quantity = (
            bool(re.search(r"\d", line))
            or any(word in lower for word in quantity_words)
        )

        if "|" not in line and not has_quantity:
            continue

        lines.append(line)

    return lines


def _step_lines(block):
    lines = []

    for line in str(block or "").splitlines():
        line = clean_text(line)

        if not line:
            continue

        parts = [
            clean_text(part)
            for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)
            if clean_text(part)
        ]
        lines.extend(parts or [line])

    return [
        line
        for line in lines
        if len(line) >= 12
    ]


def _written_recipe_title(description):
    match = re.search(
        r"Full written recipe\s*[-:]\s*(.+)",
        description or "",
        re.IGNORECASE,
    )

    if not match:
        return None

    return clean_text(match.group(1))


def _intro_text(description):
    intro = []

    for line in str(description or "").splitlines():
        stripped = line.strip()

        if re.search(r"^Full written recipe", stripped, re.IGNORECASE):
            break

        if stripped:
            intro.append(stripped)

    return " ".join(intro[:4])


def collect_youtube_recipes(
    channel_url=YOUR_FOOD_LAB_CHANNEL_URL,
    max_videos=100,
    output_dir=DEFAULT_OUTPUT_DIR,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "your_food_lab_raw_video_metadata.csv"
    normalized_path = output_dir / "your_food_lab_normalized_recipes.csv"

    videos = list_channel_videos(channel_url, max_videos)
    raw_rows = []
    normalized_rows = []

    for video in videos:
        video_id = video.get("id")

        if not video_id:
            continue

        try:
            info = fetch_video_info(video_id)
        except Exception as exc:
            raw_rows.append(
                {
                    "video_id": video_id,
                    "title": clean_text(video.get("title")),
                    "source_url": f"https://www.youtube.com/watch?v={video_id}",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        raw_rows.append(
            {
                "video_id": video_id,
                "title": clean_text(info.get("title")),
                "source_url": f"https://www.youtube.com/watch?v={video_id}",
                "duration_seconds": info.get("duration"),
                "upload_date": info.get("upload_date"),
                "description": info.get("description") or "",
                "error": "",
            }
        )

        recipe = parse_description_recipe(info)

        if recipe:
            normalized_rows.append(recipe)

    _write_csv(raw_path, raw_rows)
    _write_csv(normalized_path, normalized_rows)

    return {
        "channel_url": channel_url,
        "videos_examined": len(videos),
        "raw_metadata_rows": len(raw_rows),
        "normalized_recipe_rows": len(normalized_rows),
        "raw_path": str(raw_path),
        "normalized_path": str(normalized_path),
    }


def ingest_normalized(path, limit=None):
    records = []

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        for index, row in enumerate(reader, start=1):
            if limit is not None and len(records) >= limit:
                break

            records.append(
                RawRecord(
                    source_id=SOURCE_ID,
                    source_type="youtube",
                    _raw_content=dict(row),
                    metadata={
                        "file_path": str(path),
                        "row_number": index,
                    },
                )
            )

    pipeline = RecipePipeline(
        enricher=RecipeEnricher(
            ingredient_resolver=IngredientResolver(enable_embedding=False)
        )
    )
    return pipeline.run_records(
        records,
        source_id=SOURCE_ID,
        source_name=str(path),
        source_type="youtube",
    )


def _write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Collect and ingest structured YouTube recipe descriptions."
    )
    parser.add_argument("--channel-url", default=YOUR_FOOD_LAB_CHANNEL_URL)
    parser.add_argument("--max-videos", type=int, default=100)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--ingest-path")
    parser.add_argument("--ingest-limit", type=int)
    args = parser.parse_args()

    if args.ingest_path:
        print(ingest_normalized(args.ingest_path, args.ingest_limit))
        return

    summary = collect_youtube_recipes(
        channel_url=args.channel_url,
        max_videos=args.max_videos,
        output_dir=args.output_dir,
    )
    print(summary)

    if args.ingest:
        print(ingest_normalized(summary["normalized_path"], args.ingest_limit))


if __name__ == "__main__":
    main()
