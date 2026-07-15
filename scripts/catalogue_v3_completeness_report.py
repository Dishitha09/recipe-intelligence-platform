import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


def main():
    sql = """
    SELECT
        source,
        count(*) AS total,
        count(*) FILTER (WHERE description IS NOT NULL) AS with_description,
        count(*) FILTER (WHERE jsonb_typeof(nutrition_info) = 'object'
            AND nutrition_info <> '{}'::jsonb) AS with_nutrition,
        count(*) FILTER (WHERE array_length(tags, 1) > 0) AS with_tags,
        count(*) FILTER (WHERE jsonb_extract_path_text(metadata, 'source_url') IS NOT NULL)
            AS with_source_url,
        count(*) FILTER (WHERE servings IS NOT NULL AND servings > 0) AS with_servings,
        count(*) FILTER (WHERE image_url IS NOT NULL) AS with_image,
        count(*) FILTER (WHERE array_length(course, 1) > 0) AS with_course,
        count(*) FILTER (WHERE region IS NOT NULL) AS with_region,
        count(*) FILTER (WHERE diet IS NOT NULL) AS with_diet,
        count(*) FILTER (WHERE array_length(cuisines, 1) > 0) AS with_cuisines,
        count(*) FILTER (WHERE array_length(meal_types, 1) > 0) AS with_meal_types,
        count(*) FILTER (WHERE prep_time_min IS NOT NULL) AS with_prep_time,
        count(*) FILTER (WHERE cook_time_min IS NOT NULL) AS with_cook_time,
        count(*) FILTER (WHERE total_time_min IS NOT NULL) AS with_total_time,
        count(*) FILTER (WHERE jsonb_array_length(ingredients_json) > 0)
            AS with_ingredients,
        count(*) FILTER (WHERE jsonb_array_length(cook_steps) > 0) AS with_cook_steps,
        count(*) FILTER (WHERE array_length(quick_steps, 1) > 0) AS with_quick_steps
        ,
        count(*) FILTER (WHERE difficulty_level IS NOT NULL) AS with_difficulty,
        count(*) FILTER (WHERE array_length(diet_tags, 1) > 0) AS with_diet_tags,
        count(*) FILTER (WHERE array_length(allergen_tags, 1) > 0) AS with_allergen_tags,
        count(*) FILTER (WHERE array_length(dish_types, 1) > 0) AS with_dish_types,
        count(*) FILTER (WHERE dish_family IS NOT NULL) AS with_dish_family,
        count(*) FILTER (WHERE meal_role IS NOT NULL) AS with_meal_role,
        count(*) FILTER (WHERE array_length(health_tags, 1) > 0) AS with_health_tags,
        count(*) FILTER (WHERE array_length(efficiency_tags, 1) > 0) AS with_efficiency_tags,
        count(*) FILTER (WHERE cost_tier IS NOT NULL) AS with_cost_tier,
        count(*) FILTER (WHERE metadata ? 'catalogue_v3_enrichment') AS with_enrichment_metadata
        ,
        count(*) FILTER (
            WHERE jsonb_path_exists(ingredients_json, '$[*].name')
        ) AS with_ingredient_names,
        count(*) FILTER (
            WHERE jsonb_path_exists(ingredients_json, '$[*].quantity')
        ) AS with_ingredient_quantities,
        count(*) FILTER (
            WHERE jsonb_path_exists(ingredients_json, '$[*].canonical_unit')
        ) AS with_canonical_units,
        count(*) FILTER (
            WHERE jsonb_path_exists(ingredients_json, '$[*].conversion_method')
        ) AS with_conversion_methods
        ,
        count(*) FILTER (
            WHERE jsonb_path_exists(ingredients_json, '$[*].normalized_text')
        ) AS with_normalized_ingredient_text
    FROM recipe_catalogue_v3
    GROUP BY source
    ORDER BY total DESC
    """

    with get_catalogue_v3_engine().connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(text(sql)).mappings()
        ]

    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
