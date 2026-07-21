import csv
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_loader import CatalogueV3Loader
from services.database.fingerprints import stable_hash


MULTISOURCE_ROOT = Path("data/datasets/multisource")


def load_catalogue_v3_multisource_sidecars():
    payloads = [
        _text_payload(
            source="youtube_transcript_sidecar",
            source_type="youtube",
            path=MULTISOURCE_ROOT / "youtube/masala_dosa_transcript.txt",
            state="Karnataka",
            region="South",
            servings=4,
        ),
        _text_payload(
            source="pdf_cookbook_sidecar",
            source_type="pdf",
            path=MULTISOURCE_ROOT / "pdf/coastal_coconut_rice.txt",
            state="Kerala",
            region="South",
            servings=4,
        ),
        _text_payload(
            source="audio_transcript_sidecar",
            source_type="audio",
            path=MULTISOURCE_ROOT / "audio/karnataka_lemon_rice_transcript.txt",
            state="Karnataka",
            region="South",
            servings=4,
        ),
        _text_payload(
            source="image_ocr_sidecar",
            source_type="image_ocr",
            path=MULTISOURCE_ROOT / "images/maharashtrian_poha_ocr.txt",
            state="Maharashtra",
            region="West",
            servings=4,
            image_url="file://data/datasets/multisource/images/maharashtrian_poha_card.png",
        ),
        _text_payload(
            source="plain_text_sidecar",
            source_type="plain_text",
            path=MULTISOURCE_ROOT / "text/tamil_tomato_rasam.txt",
            state="Tamil Nadu",
            region="South",
            servings=4,
        ),
        *_csv_payloads(
            source="csv_manual_upload",
            source_type="csv_manual",
            path=MULTISOURCE_ROOT / "csv/manual_recipe_upload.csv",
        ),
    ]

    loader = CatalogueV3Loader()
    inserted = 0
    skipped_existing = 0
    inserted_ids = []

    with get_catalogue_v3_engine().begin() as conn:
        for payload in payloads:
            content_hash = payload["metadata"]["content_hash"]
            exists = conn.execute(
                text(
                    """
                    SELECT recipe_id
                    FROM recipe_catalogue_v3
                    WHERE metadata->>'content_hash' = :content_hash
                       OR metadata->>'source_url' = :source_url
                    LIMIT 1
                    """
                ),
                {
                    "content_hash": content_hash,
                    "source_url": payload["metadata"]["source_url"],
                },
            ).scalar()

            if exists:
                skipped_existing += 1
                continue

            inserted_ids.append(loader.insert_recipe(payload))
            inserted += 1

    return {
        "selected": len(payloads),
        "inserted": inserted,
        "skipped_existing": skipped_existing,
        "inserted_ids": inserted_ids,
        "sources": sorted({payload["source"] for payload in payloads}),
    }


def _text_payload(source, source_type, path, state, region, servings, image_url=None):
    text_value = Path(path).read_text(encoding="utf-8")
    title, ingredients, instructions = _parse_recipe_text(text_value)
    source_url = f"file://{Path(path).as_posix()}"
    metadata = _metadata(
        source=source,
        source_type=source_type,
        source_url=source_url,
        raw_text=text_value,
    )

    return _payload(
        name=title,
        description=f"Recipe extracted from {source_type} sidecar: {title}.",
        source=source,
        source_type=source_type,
        source_url=source_url,
        metadata=metadata,
        state=state,
        region=region,
        servings=servings,
        ingredients=ingredients,
        instructions=instructions,
        image_url=image_url,
    )


def _csv_payloads(source, source_type, path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ingredients = [
                item.strip()
                for item in row["ingredients"].split("|")
                if item.strip()
            ]
            instructions = [
                item.strip()
                for item in row["instructions"].split("|")
                if item.strip()
            ]
            source_url = row["source_url"]
            metadata = _metadata(
                source=source,
                source_type=source_type,
                source_url=source_url,
                raw_text=json.dumps(row, ensure_ascii=False),
            )
            yield _payload(
                name=row["title"],
                description=row["description"],
                source=source,
                source_type=source_type,
                source_url=source_url,
                metadata=metadata,
                state=row["state"],
                region=row["region"],
                servings=4,
                ingredients=ingredients,
                instructions=instructions,
            )


def _parse_recipe_text(text_value):
    lines = [
        line.strip()
        for line in text_value.splitlines()
        if line.strip()
    ]
    title = lines[0]
    ingredients = []
    instructions = []
    section = None

    for line in lines[1:]:
        normalized = line.lower().rstrip(":")

        if normalized == "ingredients":
            section = "ingredients"
            continue

        if normalized == "instructions":
            section = "instructions"
            continue

        if section == "ingredients":
            ingredients.append(line)
        elif section == "instructions":
            instructions.append(line)

    return title, ingredients, instructions


def _payload(
    name,
    description,
    source,
    source_type,
    source_url,
    metadata,
    state,
    region,
    servings,
    ingredients,
    instructions,
    image_url=None,
):
    return {
        "name": name,
        "description": description,
        "metadata": metadata,
        "servings": servings,
        "image_url": image_url,
        "course": ["main"],
        "region": region,
        "cuisines": ["Indian", state],
        "meal_types": ["lunch", "dinner"],
        "ingredients_json": [
            {
                "raw_text": ingredient,
                "source_position": index,
            }
            for index, ingredient in enumerate(ingredients, start=1)
        ],
        "cook_steps": [
            {
                "step_number": index,
                "instruction": instruction,
            }
            for index, instruction in enumerate(instructions, start=1)
        ],
        "quick_steps": instructions[:3],
        "source": source,
        "language": "en",
        "is_public": True,
        "created_by": "multisource_sidecar_loader",
        "is_active": True,
        "tags": [source_type, "indian"],
        "diet": None,
        "prep_time_min": None,
        "cook_time_min": None,
        "total_time_min": None,
        "owner_code": None,
        "owner_name": None,
    }


def _metadata(source, source_type, source_url, raw_text):
    return {
        "source": source,
        "source_type": source_type,
        "source_url": source_url,
        "content_hash": stable_hash(
            {
                "source": source,
                "source_type": source_type,
                "source_url": source_url,
                "raw_text": raw_text,
            }
        ),
        "generated_text": False,
        "loader": "load_catalogue_v3_multisource_sidecars",
    }


def main():
    print(
        json.dumps(
            load_catalogue_v3_multisource_sidecars(),
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
