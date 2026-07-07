import argparse
import json
from pathlib import Path

from sqlalchemy import text

from services.database.connection import engine
from services.enrichment.ingredient_resolution.ingredient_resolver import (
    IngredientResolver,
)
from services.enrichment.recipe_enricher import RecipeEnricher
from services.ingestion.audio_adapter import AudioAdapter
from services.ingestion.csv_adapter import CSVAdapter
from services.ingestion.dataset_adapter import DatasetAdapter
from services.ingestion.image_adapter import ImageAdapter
from services.ingestion.pdf_adapter import PDFAdapter
from services.ingestion.youtube_adapter import YouTubeAdapter
from services.pipeline.recipe_pipeline import RecipePipeline


ROOT = Path("data/datasets/multisource")


def _ensure_audio_placeholder(path):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_bytes(b"")


def _ensure_image_card(image_path, text_path):
    image_path.parent.mkdir(parents=True, exist_ok=True)

    if image_path.exists():
        return

    from PIL import Image, ImageDraw

    text = text_path.read_text(encoding="utf-8")
    lines = text.splitlines()[:18]
    image = Image.new("RGB", (1000, 900), "white")
    draw = ImageDraw.Draw(image)
    y = 32

    for line in lines:
        draw.text((32, y), line[:105], fill="black")
        y += 42

    image.save(image_path)


def _ensure_pdf(pdf_path, text_path):
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if pdf_path.exists():
        return

    pdf_path.write_bytes(b"%PDF-1.4\n% ShopConnect sidecar fixture\n%%EOF\n")


def ensure_artifacts():
    audio_path = ROOT / "audio" / "karnataka_lemon_rice.mp3"
    image_path = ROOT / "images" / "maharashtrian_poha_card.png"
    image_text_path = ROOT / "images" / "maharashtrian_poha_ocr.txt"
    pdf_path = ROOT / "pdf" / "coastal_coconut_rice.pdf"
    pdf_text_path = ROOT / "pdf" / "coastal_coconut_rice.txt"

    _ensure_audio_placeholder(audio_path)
    _ensure_image_card(image_path, image_text_path)
    _ensure_pdf(pdf_path, pdf_text_path)

    return {
        "audio_path": audio_path,
        "image_path": image_path,
        "pdf_path": pdf_path,
    }


def build_sources():
    artifacts = ensure_artifacts()

    return [
        {
            "label": "youtube transcript",
            "source_id": "youtube.default",
            "source_type": "youtube",
            "source_name": "masala_dosa_transcript.txt",
            "adapter": YouTubeAdapter(
                "local-masala-dosa-transcript",
                config={
                    "title": "Masala Dosa YouTube Transcript",
                    "transcript_path": str(
                        ROOT / "youtube" / "masala_dosa_transcript.txt"
                    ),
                    "source_url": (
                        "file://data/datasets/multisource/youtube/"
                        "masala_dosa_transcript.txt"
                    ),
                },
            ),
        },
        {
            "label": "PDF cookbook",
            "source_id": "pdf.default",
            "source_type": "pdf",
            "source_name": "coastal_coconut_rice.pdf",
            "adapter": PDFAdapter(
                str(artifacts["pdf_path"]),
                config={
                    "title": "Coastal Coconut Rice Cookbook Page",
                    "text_path": str(ROOT / "pdf" / "coastal_coconut_rice.txt"),
                    "source_url": (
                        "file://data/datasets/multisource/pdf/"
                        "coastal_coconut_rice.pdf"
                    ),
                },
            ),
        },
        {
            "label": "structured dataset",
            "source_id": "dataset.default",
            "source_type": "dataset",
            "source_name": "structured_indian_recipes.csv",
            "adapter": DatasetAdapter(
                str(ROOT / "datasets" / "structured_indian_recipes.csv")
            ),
        },
        {
            "label": "image OCR",
            "source_id": "image.default",
            "source_type": "image",
            "source_name": "maharashtrian_poha_card.png",
            "adapter": ImageAdapter(
                str(artifacts["image_path"]),
                config={
                    "title": "Maharashtrian Kanda Poha Recipe Card",
                    "ocr_text_path": str(
                        ROOT / "images" / "maharashtrian_poha_ocr.txt"
                    ),
                    "source_url": (
                        "file://data/datasets/multisource/images/"
                        "maharashtrian_poha_card.png"
                    ),
                },
            ),
        },
        {
            "label": "audio transcript",
            "source_id": "audio.default",
            "source_type": "audio",
            "source_name": "karnataka_lemon_rice.mp3",
            "adapter": AudioAdapter(
                str(artifacts["audio_path"]),
                config={
                    "title": "Karnataka Lemon Rice Audio Transcript",
                    "transcript_path": str(
                        ROOT / "audio" / "karnataka_lemon_rice_transcript.txt"
                    ),
                    "source_url": (
                        "file://data/datasets/multisource/audio/"
                        "karnataka_lemon_rice.mp3"
                    ),
                },
            ),
        },
        {
            "label": "manual CSV upload",
            "source_id": "csv.default",
            "source_type": "csv",
            "source_name": "manual_recipe_upload.csv",
            "adapter": CSVAdapter(
                str(ROOT / "csv" / "manual_recipe_upload.csv")
            ),
        },
    ]


def source_type_counts():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT source_type, count(*) AS recipe_count
                FROM recipes
                GROUP BY source_type
                ORDER BY source_type
                """
            )
        ).mappings()

        return {row["source_type"]: row["recipe_count"] for row in rows}


def main():
    parser = argparse.ArgumentParser(
        description="Ingest non-web recipe sources through their adapters."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract records without writing them to PostgreSQL.",
    )
    args = parser.parse_args()

    pipeline = RecipePipeline(
        enricher=RecipeEnricher(
            ingredient_resolver=IngredientResolver(enable_embedding=False)
        )
    )
    results = []

    for source in build_sources():
        raw_records = source["adapter"].extract()

        if args.dry_run:
            results.append(
                {
                    "label": source["label"],
                    "records_found": len(raw_records),
                }
            )
            continue

        summary = pipeline.run_records(
            raw_records,
            source_id=source["source_id"],
            source_name=source["source_name"],
            source_type=source["source_type"],
        )
        results.append(
            {
                "label": source["label"],
                "source_type": source["source_type"],
                "records_found": summary["records_found"],
                "accepted": summary["accepted"],
                "loaded": summary["loaded"],
                "review": summary["review"],
                "rejected": summary["rejected"],
                "ingestion_run_id": summary["ingestion_run_id"],
            }
        )

    output = {"sources": results}

    if not args.dry_run:
        output["source_type_counts"] = source_type_counts()

    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
