import argparse
import csv
import json
from pathlib import Path

from sqlalchemy import text

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_loader import CatalogueV3Loader


DEFAULT_INPUT = (
    "data/datasets/huggingface_indian/processed/"
    "nileshiq_indian_food_normalized.csv"
)


def load_catalogue_v3_from_normalized_dataset(
    input_path=DEFAULT_INPUT,
    limit=None,
    skip_existing=True,
    update_existing=False,
):
    input_path = Path(input_path)
    loader = CatalogueV3Loader()
    inserted = 0
    skipped = 0
    failed = 0
    errors = []

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(reader, start=1):
            if limit is not None and (inserted + skipped + failed) >= limit:
                break

            payload = row_to_catalogue_v3_payload(row, row_number, input_path)

            if skip_existing and source_url_exists(payload["metadata"].get("source_url")):
                if update_existing:
                    update_existing_source_row(payload)

                skipped += 1
                continue

            try:
                loader.insert_recipe(payload)
                inserted += 1
            except Exception as exc:
                failed += 1
                errors.append(
                    {
                        "row_number": row_number,
                        "name": payload.get("name"),
                        "error": str(exc),
                    }
                )

                if len(errors) >= 10:
                    break

    return {
        "input": str(input_path),
        "inserted": inserted,
        "skipped_existing": skipped,
        "failed": failed,
        "errors": errors,
    }


def row_to_catalogue_v3_payload(row, row_number, input_path):
    title = clean(row.get("title"))
    cuisine = clean(row.get("cuisine"))
    source_url = clean(row.get("source_url"))
    dataset_source = clean(row.get("dataset_source")) or "normalized_dataset"
    ingredients = split_pipe(row.get("ingredients"))
    steps = split_pipe(row.get("instructions"))
    course = split_pipe(row.get("course")) or []
    diet = clean(row.get("diet")).lower() or None

    return {
        "name": title,
        "description": clean(row.get("description")) or cuisine or None,
        "nutrition_info": {},
        "tags": [],
        "metadata": {
            "source_url": source_url,
            "dataset_source": dataset_source,
            "external_dataset_row": clean(row.get("external_dataset_row")),
            "input_path": str(input_path),
            "input_row_number": row_number,
        },
        "servings": to_int(row.get("servings"), default=1),
        "difficulty_level": None,
        "youtube_url": None,
        "image_url": clean(row.get("image_url")) or None,
        "course": [item.lower() for item in course],
        "region": None,
        "diet": diet,
        "spice_level": None,
        "complexity": None,
        "budget_band": None,
        "diet_tags": diet_tags_from_diet(diet),
        "allergen_tags": [],
        "cuisines": [cuisine] if cuisine else [],
        "meal_types": meal_types_from_course(course),
        "dish_types": [],
        "texture": [],
        "prep_time_min": to_int(row.get("prep_time_min")),
        "cook_time_min": to_int(row.get("cook_time_min")),
        "total_time_min": to_int(row.get("total_time_min")),
        "passive_time_min": None,
        "ingredients_json": [
            {
                "raw_text": ingredient,
                "name": ingredient,
                "source": "dataset",
            }
            for ingredient in ingredients
        ],
        "prep_steps": [],
        "cook_steps": [
            {
                "step_number": index,
                "instruction": step,
            }
            for index, step in enumerate(steps, start=1)
        ],
        "quick_steps": steps[:5],
        "estimated_cost_per_serving": None,
        "popularity_score": 0,
        "side_category": None,
        "meal_role": None,
        "dish_family": None,
        "health_tags": [],
        "efficiency_tags": [],
        "experience_tags": [],
        "cost_tier": None,
        "festival_tags": [],
        "owner_code": None,
        "owner_name": None,
        "source": dataset_source,
        "language": language_code(row.get("language")),
        "is_public": False,
        "created_by": "system_seed",
        "is_active": True,
    }


def source_url_exists(source_url):
    if not source_url:
        return False

    with get_catalogue_v3_engine().connect() as conn:
        return bool(
            conn.execute(
                text(
                    """
                    SELECT 1
                    FROM recipe_catalogue_v3
                    WHERE metadata->>'source_url' = :source_url
                    LIMIT 1
                    """
                ),
                {"source_url": source_url},
            ).scalar()
        )


def update_existing_source_row(payload):
    source_url = payload["metadata"].get("source_url")

    if not source_url:
        return 0

    update_sql = text(
        """
        UPDATE recipe_catalogue_v3
        SET
            image_url = COALESCE(NULLIF(image_url, ''), :image_url),
            metadata = metadata || CAST(:metadata_patch AS jsonb)
        WHERE metadata->>'source_url' = :source_url
        """
    )

    metadata_patch = {
        "image_source": payload.get("source"),
        "image_dataset_row": payload["metadata"].get("external_dataset_row"),
    }

    with get_catalogue_v3_engine().begin() as conn:
        result = conn.execute(
            update_sql,
            {
                "source_url": source_url,
                "image_url": payload.get("image_url"),
                "metadata_patch": json.dumps(metadata_patch),
            },
        )

    return result.rowcount or 0


def split_pipe(value):
    return [
        clean(part)
        for part in str(value or "").split("|")
        if clean(part)
    ]


def clean(value):
    return " ".join(str(value or "").split()).strip()


def to_int(value, default=None):
    value = clean(value)

    if not value:
        return default

    try:
        return int(float(value))
    except ValueError:
        return default


def language_code(value):
    value = clean(value).lower()

    if value in {"english", "en", ""}:
        return "en"

    return value


def diet_tags_from_diet(diet):
    if not diet:
        return []

    tags = []

    if "vegetarian" in diet:
        tags.append("VEGETARIAN")

    if "vegan" in diet:
        tags.append("VEGAN")

    return tags


def meal_types_from_course(course):
    text = " ".join(course).lower()
    meal_types = []

    for token in ["breakfast", "lunch", "dinner", "snack"]:
        if token in text:
            meal_types.append(token)

    return meal_types


def main():
    parser = argparse.ArgumentParser(
        description="Load normalized Indian recipe CSV rows into Catalogue V3."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Insert rows even when metadata.source_url already exists.",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update matching source_url rows with source-provided image metadata.",
    )
    args = parser.parse_args()

    print(
        json.dumps(
            load_catalogue_v3_from_normalized_dataset(
                input_path=args.input,
                limit=args.limit,
                skip_existing=not args.allow_duplicates,
                update_existing=args.update_existing,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
