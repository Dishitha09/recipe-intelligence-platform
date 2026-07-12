import argparse
import csv
from pathlib import Path

from sqlalchemy import text

from services.database.connection import engine


EXPORT_SQL = """
WITH dataset_sources_raw AS (
    SELECT
        recipe_id,
        source_name AS dataset_source_name,
        source_url AS dataset_source_url,
        run_id,
        ingested_at
    FROM recipe_source_tracking
    WHERE source_type = 'dataset'

    UNION

    SELECT
        recipe_id,
        'recipes.source_type=dataset' AS dataset_source_name,
        source_url AS dataset_source_url,
        NULL::integer AS run_id,
        created_at AS ingested_at
    FROM recipes
    WHERE source_type = 'dataset'
),
dataset_sources AS (
    SELECT
        recipe_id,
        STRING_AGG(DISTINCT dataset_source_name, ' | ') AS dataset_source_names,
        STRING_AGG(DISTINCT dataset_source_url, ' | ') AS dataset_source_urls,
        STRING_AGG(DISTINCT run_id::text, ' | ') FILTER (
            WHERE run_id IS NOT NULL
        ) AS dataset_ingestion_run_ids,
        MAX(ingested_at) AS latest_dataset_ingested_at
    FROM dataset_sources_raw
    GROUP BY recipe_id
),
ingredient_lines AS (
    SELECT
        recipe_id,
        STRING_AGG(
            CONCAT_WS(
                ' ',
                NULLIF(TRIM(TRAILING '.0' FROM quantity::text), ''),
                unit,
                ingredient_name
            ),
            ', '
            ORDER BY recipe_ingredient_id
        ) AS ingredients,
        COUNT(*) AS ingredient_count
    FROM recipe_ingredients
    GROUP BY recipe_id
)
SELECT
    r.recipe_id,
    r.title,
    r.state,
    r.region,
    r.source_type AS primary_source_type,
    r.source_url AS primary_source_url,
    ds.dataset_source_names,
    ds.dataset_source_urls,
    ds.dataset_ingestion_run_ids,
    ds.latest_dataset_ingested_at,
    COALESCE(il.ingredient_count, 0) AS ingredient_count,
    r.step_count,
    il.ingredients,
    r.instructions_one_line AS instructions
FROM dataset_sources ds
JOIN recipe_with_instructions r
    ON r.recipe_id = ds.recipe_id
LEFT JOIN ingredient_lines il
    ON il.recipe_id = r.recipe_id
ORDER BY
    r.title,
    r.recipe_id
"""


FIELDS = [
    "recipe_id",
    "title",
    "state",
    "region",
    "primary_source_type",
    "primary_source_url",
    "dataset_source_names",
    "dataset_source_urls",
    "dataset_ingestion_run_ids",
    "latest_dataset_ingested_at",
    "ingredient_count",
    "step_count",
    "ingredients",
    "instructions",
]


def export_dataset_recipes(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        rows = conn.execute(text(EXPORT_SQL)).mappings().all()

    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    distinct_recipe_ids = {row["recipe_id"] for row in rows}

    return {
        "path": str(output_path),
        "rows": len(rows),
        "distinct_recipes": len(distinct_recipe_ids),
        "bytes": output_path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Export production dataset recipe provenance from PostgreSQL."
    )
    parser.add_argument(
        "--output",
        default="data/datasets/production/real_dataset_recipes_50_20260712.csv",
    )
    args = parser.parse_args()

    print(export_dataset_recipes(args.output))


if __name__ == "__main__":
    main()
