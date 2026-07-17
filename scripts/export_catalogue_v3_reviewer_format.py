import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


DEFAULT_OUTPUT = Path(
    "data/datasets/catalogue_v3/exports/catalogue_v3_reviewer_format.csv"
)

EXPORT_COLUMNS = [
    "name",
    "course",
    "region",
    "cuisines",
    "meal_types",
    "ingredients_json",
    "description",
    "servings",
    "difficulty_level",
    "youtube_url",
    "image_url",
    "prep_steps",
    "cook_steps",
    "quick_steps",
    "nutrition_info",
    "tags",
    "metadata",
    "diet",
    "complexity",
    "spice_level",
    "budget_band",
    "dish_types",
    "texture",
    "diet_tags",
    "allergen_tags",
    "health_tags",
    "efficiency_tags",
    "experience_tags",
    "cost_tier",
    "side_category",
    "dish_family",
    "festival_tags",
    "prep_time_min",
    "cook_time_min",
    "total_time_min",
    "passive_time_min",
    "estimated_cost_per_serving",
    "popularity_score",
    "owner_code",
    "owner_name",
    "source",
    "source_url",
    "language",
    "is_public",
    "created_by",
    "is_active",
    "meal_role",
    "created_at",
    "updated_at",
]


SELECT_SQL = text(
    """
    SELECT
        name,
        description,
        nutrition_info,
        tags,
        metadata,
        servings,
        difficulty_level,
        youtube_url,
        image_url,
        course,
        region,
        diet,
        spice_level,
        complexity,
        budget_band,
        diet_tags,
        allergen_tags,
        cuisines,
        meal_types,
        dish_types,
        texture,
        prep_time_min,
        cook_time_min,
        total_time_min,
        passive_time_min,
        ingredients_json,
        prep_steps,
        cook_steps,
        quick_steps,
        estimated_cost_per_serving,
        popularity_score,
        side_category,
        meal_role,
        dish_family,
        health_tags,
        efficiency_tags,
        experience_tags,
        cost_tier,
        festival_tags,
        owner_code,
        owner_name,
        source,
        metadata->>'source_url' AS source_url,
        language,
        is_public,
        created_by,
        is_active,
        created_at,
        updated_at
    FROM recipe_catalogue_v3
    WHERE (:active_only IS FALSE OR is_active IS TRUE)
    ORDER BY created_at, name
    """
)


def export_catalogue_v3_reviewer_format(
    output_path=DEFAULT_OUTPUT,
    active_only=False,
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with get_catalogue_v3_engine().connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                SELECT_SQL,
                {"active_only": active_only},
            ).mappings()
        ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()

        for row in rows:
            writer.writerow(_export_row(row))

    return {
        "output_csv": str(output_path),
        "rows_exported": len(rows),
        "active_only": active_only,
        "columns": EXPORT_COLUMNS,
    }


def _export_row(row):
    exported = {}

    for column in EXPORT_COLUMNS:
        value = row.get(column)

        if column == "ingredients_json":
            value = _reviewer_ingredients(row.get("ingredients_json") or [])

        exported[column] = _cell(value)

    return exported


def _reviewer_ingredients(ingredients):
    reviewer_items = []

    for ingredient in ingredients:
        item = ingredient.get("name") or ingredient.get("item")
        item, prep = _split_item_prep(
            item or ingredient.get("raw_text"),
            ingredient.get("prep") or ingredient.get("preparation"),
        )
        quantity = ingredient.get("quantity")
        unit = ingredient.get("unit") or None
        normalized_quantity = ingredient.get("canonical_quantity")
        normalized_unit = ingredient.get("canonical_unit") or None

        reviewer_items.append(
            {
                "item": item,
                "quantity": _number(quantity),
                "unit": unit,
                "normalized_quantity": _number(normalized_quantity),
                "normalized_unit": normalized_unit,
                "normalized_text": ingredient.get("normalized_text"),
                "prep": prep,
            }
        )

    return reviewer_items


def _split_item_prep(item_text, prep):
    item_text = str(item_text or "").strip()
    prep = str(prep).strip() if prep else None

    if not prep and " - " in item_text:
        item_text, prep = item_text.split(" - ", 1)
        prep = prep.strip() or None

    item_text = re.sub(
        (
            r"^\s*(?:\d+(?:-\d+/\d+)?(?:\.\d+)?|\d+/\d+|"
            r"\d+\s+\d+/\d+|\d+\s+to\s+\d+(?:\.\d+)?)\s*"
            r"(?:cups?|teaspoons?|tablespoons?|tbsp|tsp|grams?|gram|g|kg|"
            r"ml|milliliters?|millilitres?|ounces?|ounce|oz|pounds?|pound|"
            r"lb|lbs|cloves?|pieces?|slices?|sprigs?|inch|inches)?\s*"
        ),
        "",
        item_text,
        flags=re.I,
    )
    item_text = item_text.strip()

    return item_text or None, prep


def _cell(value):
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=_json_default)

    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"

    if value is None:
        return ""

    return _json_default(value)


def _number(value):
    if value is None:
        return None

    try:
        value = round(float(value), 2)
    except (TypeError, ValueError):
        return value

    if value.is_integer():
        return int(value)

    return value


def _json_default(value):
    if isinstance(value, Decimal):
        return _number(value)

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Export recipe_catalogue_v3 in reviewer schema order with "
            "metric item/quantity/unit ingredient objects."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--active-only", action="store_true")
    args = parser.parse_args()

    print(
        json.dumps(
            export_catalogue_v3_reviewer_format(
                output_path=args.output,
                active_only=args.active_only,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
