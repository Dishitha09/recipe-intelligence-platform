import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


TARGET_SOURCES = [
    "swasthi_recipes_index_web",
    "veg_recipes_of_india_web",
    "archanas_kitchen_web",
    "whiskaffair_indian_state_web",
    "sailus_food_web",
    "eat_by_state_web",
    "vegan_richa_indian_web",
]


SOURCE_COUNTS_SQL = text(
    """
    SELECT
        source,
        count(*) AS total,
        count(*) FILTER (WHERE metadata->>'source_url' IS NOT NULL)
            AS with_source_url,
        count(*) FILTER (WHERE jsonb_array_length(ingredients_json) > 0)
            AS with_ingredients,
        count(*) FILTER (WHERE jsonb_array_length(cook_steps) > 0)
            AS with_steps,
        count(*) FILTER (WHERE servings IS NOT NULL)
            AS with_servings
    FROM recipe_catalogue_v3
    WHERE source = ANY(:sources)
    GROUP BY source
    ORDER BY source
    """
)


SAMPLE_SQL = text(
    """
    SELECT
        recipe_id,
        source,
        name,
        metadata->>'source_url' AS source_url
    FROM recipe_catalogue_v3
    WHERE source = ANY(:sources)
    ORDER BY created_at DESC, recipe_id DESC
    LIMIT :limit
    """
)


def target_webpage_schema_v3_counts(sample_limit=15):
    with get_catalogue_v3_engine().connect() as conn:
        counts = [
            dict(row)
            for row in conn.execute(
                SOURCE_COUNTS_SQL,
                {"sources": TARGET_SOURCES},
            ).mappings()
        ]
        samples = [
            dict(row)
            for row in conn.execute(
                SAMPLE_SQL,
                {"sources": TARGET_SOURCES, "limit": sample_limit},
            ).mappings()
        ]

    return {
        "target_sources": TARGET_SOURCES,
        "counts": counts,
        "samples": samples,
    }


def main():
    print(
        json.dumps(
            target_webpage_schema_v3_counts(),
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
