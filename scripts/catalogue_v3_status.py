import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


def main():
    summary_sql = """
    SELECT
        count(*) AS total,
        count(*) FILTER (
            WHERE jsonb_array_length(ingredients_json) > 0
        ) AS with_ingredients,
        count(*) FILTER (
            WHERE jsonb_array_length(cook_steps) > 0
        ) AS with_steps,
        count(*) FILTER (WHERE servings > 0) AS with_servings,
        count(*) FILTER (WHERE prep_time_min IS NOT NULL) AS with_prep,
        count(*) FILTER (WHERE cook_time_min IS NOT NULL) AS with_cook,
        count(*) FILTER (WHERE image_url IS NOT NULL) AS with_images
    FROM recipe_catalogue_v3
    """
    sample_sql = """
    SELECT
        name,
        servings,
        diet,
        cuisines,
        meal_types,
        source,
        metadata->>'source_url' AS source_url
    FROM recipe_catalogue_v3
    ORDER BY created_at DESC
    LIMIT 5
    """
    index_sql = """
    SELECT count(*)
    FROM pg_indexes
    WHERE tablename = 'recipe_catalogue_v3'
    """

    with get_catalogue_v3_engine().connect() as conn:
        summary = dict(conn.execute(text(summary_sql)).mappings().one())
        samples = [
            dict(row)
            for row in conn.execute(text(sample_sql)).mappings()
        ]
        index_count = conn.execute(text(index_sql)).scalar_one()

    print({"summary": summary, "index_count": index_count})
    print({"samples": samples})


if __name__ == "__main__":
    main()
