import argparse
import csv
from pathlib import Path

from sqlalchemy import text

from services.database.connection import engine


EXPORT_SQL = """
WITH ingredient_lines AS (
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
    r.title,
    r.state,
    r.region,
    r.source_type,
    r.source_url,
    COALESCE(il.ingredient_count, 0) AS ingredient_count,
    r.step_count,
    il.ingredients,
    r.instructions_one_line AS instructions
FROM recipe_with_instructions r
LEFT JOIN ingredient_lines il
    ON il.recipe_id = r.recipe_id
WHERE r.source_type = 'web'
ORDER BY r.title, r.source_url
"""


FIELDS = [
    "title",
    "state",
    "region",
    "source_type",
    "source_url",
    "ingredient_count",
    "step_count",
    "ingredients",
    "instructions",
]


def export_web_recipes(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        rows = conn.execute(text(EXPORT_SQL)).mappings().all()

    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "path": str(output_path),
        "rows": len(rows),
        "bytes": output_path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Export production web recipe dataset from PostgreSQL."
    )
    parser.add_argument(
        "--output",
        default="data/datasets/production/real_web_recipes_1629_20260708.csv",
    )
    args = parser.parse_args()

    print(export_web_recipes(args.output))


if __name__ == "__main__":
    main()
