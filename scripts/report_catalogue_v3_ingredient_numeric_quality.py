import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


QUALITY_SQL = text(
    """
    WITH ingredient_items AS (
        SELECT
            recipe_id,
            source,
            ingredient
        FROM recipe_catalogue_v3
        CROSS JOIN LATERAL jsonb_array_elements(ingredients_json) AS ingredient
    )
    SELECT
        count(*) AS ingredient_rows,
        count(*) FILTER (
            WHERE ingredient ? 'quantity'
              AND jsonb_typeof(ingredient->'quantity') = 'string'
        ) AS string_quantity_rows,
        count(*) FILTER (
            WHERE ingredient ? 'canonical_quantity'
              AND jsonb_typeof(ingredient->'canonical_quantity') = 'string'
        ) AS string_canonical_quantity_rows,
        count(*) FILTER (
            WHERE ingredient ? 'conversion_factor'
              AND jsonb_typeof(ingredient->'conversion_factor') = 'string'
        ) AS string_conversion_factor_rows,
        count(*) FILTER (
            WHERE ingredient ? 'quantity'
              AND jsonb_typeof(ingredient->'quantity') = 'number'
              AND (ingredient->>'quantity') ~ '\\.[0-9]{3,}$'
        ) AS long_decimal_quantity_rows,
        count(*) FILTER (
            WHERE ingredient ? 'canonical_quantity'
              AND jsonb_typeof(ingredient->'canonical_quantity') = 'number'
              AND (ingredient->>'canonical_quantity') ~ '\\.[0-9]{3,}$'
        ) AS long_decimal_canonical_quantity_rows,
        count(*) FILTER (
            WHERE ingredient ? 'conversion_factor'
              AND jsonb_typeof(ingredient->'conversion_factor') = 'number'
              AND (ingredient->>'conversion_factor') ~ '\\.[0-9]{3,}$'
        ) AS long_decimal_conversion_factor_rows,
        count(*) FILTER (
            WHERE ingredient ? 'canonical_unit'
              AND ingredient->>'canonical_unit' IN ('cup', 'tsp', 'tbsp')
        ) AS non_metric_canonical_unit_rows
    FROM ingredient_items
    """
)


UNIT_COUNTS_SQL = text(
    """
    SELECT
        ingredient->>'canonical_unit' AS canonical_unit,
        count(*) AS total
    FROM recipe_catalogue_v3
    CROSS JOIN LATERAL jsonb_array_elements(ingredients_json) AS ingredient
    WHERE ingredient ? 'canonical_unit'
    GROUP BY ingredient->>'canonical_unit'
    ORDER BY total DESC
    """
)


SAMPLES_SQL = text(
    """
    SELECT
        source,
        name,
        ingredient
    FROM recipe_catalogue_v3
    CROSS JOIN LATERAL jsonb_array_elements(ingredients_json) AS ingredient
    WHERE ingredient ? 'quantity'
      AND jsonb_typeof(ingredient->'quantity') = 'number'
    ORDER BY updated_at DESC, created_at DESC
    LIMIT :limit
    """
)


def ingredient_numeric_quality(sample_limit=12):
    with get_catalogue_v3_engine().connect() as conn:
        quality = dict(conn.execute(QUALITY_SQL).mappings().one())
        unit_counts = [
            dict(row)
            for row in conn.execute(UNIT_COUNTS_SQL).mappings()
        ]
        samples = [
            dict(row)
            for row in conn.execute(
                SAMPLES_SQL,
                {"limit": sample_limit},
            ).mappings()
        ]

    return {
        "quality": quality,
        "canonical_unit_counts": unit_counts,
        "samples": samples,
    }


def main():
    print(
        json.dumps(
            ingredient_numeric_quality(),
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
