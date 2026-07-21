import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


SOURCE_TYPE_RULES = {
    "youtube": ("youtube", "yt_"),
    "dataset": ("dataset", "huggingface", "kaggle", "csv_dataset"),
    "pdf": ("pdf", "cookbook"),
    "audio": ("audio", "transcript_audio"),
    "image_ocr": ("image", "ocr"),
    "plain_text": ("plain_text", "text_"),
    "csv_manual": ("manual", "csv_manual", "csv_upload"),
}


def catalogue_v3_multisource_evidence_report(
    output_path=Path("evidence/catalogue_v3_multisource_evidence_latest.json"),
):
    with get_catalogue_v3_engine().connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT
                        source,
                        youtube_url,
                        metadata,
                        count(*) AS recipe_count,
                        count(*) FILTER (
                            WHERE jsonb_array_length(ingredients_json) > 0
                        ) AS with_ingredients,
                        count(*) FILTER (
                            WHERE jsonb_array_length(cook_steps) > 0
                        ) AS with_steps,
                        count(*) FILTER (WHERE image_url IS NOT NULL)
                            AS with_image,
                        count(*) FILTER (WHERE servings IS NOT NULL)
                            AS with_servings,
                        count(*) FILTER (WHERE language = 'en')
                            AS english_rows
                    FROM recipe_catalogue_v3
                    WHERE is_active IS TRUE
                    GROUP BY source, youtube_url, metadata
                    """
                )
            ).mappings()
        ]

    by_source = defaultdict(
        lambda: {
            "source_type": None,
            "recipe_count": 0,
            "with_ingredients": 0,
            "with_steps": 0,
            "with_image": 0,
            "with_servings": 0,
            "english_rows": 0,
        }
    )
    by_source_type = defaultdict(int)

    for row in rows:
        source = row["source"] or "unknown"
        source_type = _classify_source_type(row)
        item = by_source[source]
        item["source_type"] = source_type

        for key in [
            "recipe_count",
            "with_ingredients",
            "with_steps",
            "with_image",
            "with_servings",
            "english_rows",
        ]:
            item[key] += int(row[key] or 0)

        by_source_type[source_type] += int(row["recipe_count"] or 0)

    total = sum(by_source_type.values())
    required_types = [
        "web",
        "youtube",
        "dataset",
        "pdf",
        "audio",
        "image_ocr",
        "plain_text",
        "csv_manual",
    ]
    covered_types = [
        source_type
        for source_type in required_types
        if by_source_type.get(source_type, 0) > 0
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": "recipe_catalogue_v3",
        "total_recipes": total,
        "source_type_counts": dict(sorted(by_source_type.items())),
        "required_source_types": required_types,
        "covered_source_types": covered_types,
        "missing_source_types": [
            source_type
            for source_type in required_types
            if source_type not in covered_types
        ],
        "passes_multisource_presence": len(covered_types) == len(required_types),
        "sources": dict(sorted(by_source.items())),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
    report["output_path"] = str(output_path)
    return report


def _classify_source_type(row):
    source = str(row.get("source") or "").lower()
    metadata = row.get("metadata") or {}
    metadata_source_type = str(metadata.get("source_type") or "").lower()
    metadata_source = str(metadata.get("source") or "").lower()
    combined = " ".join([source, metadata_source_type, metadata_source])

    if row.get("youtube_url"):
        return "youtube"

    for source_type, markers in SOURCE_TYPE_RULES.items():
        if any(marker in combined for marker in markers):
            return source_type

    return "web"


def main():
    print(
        json.dumps(
            catalogue_v3_multisource_evidence_report(),
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
