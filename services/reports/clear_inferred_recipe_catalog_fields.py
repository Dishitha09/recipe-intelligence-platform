import json

from sqlalchemy import text

from services.database.connection import engine


def clear_inferred_fields():
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE recipes
                SET
                    nutrition_info = '{}'::jsonb,
                    tags = ARRAY[]::TEXT[],
                    servings = NULL,
                    difficulty_level = NULL,
                    image_url = NULL,
                    course = ARRAY[]::TEXT[],
                    diet = NULL,
                    spice_level = NULL,
                    complexity = NULL,
                    budget_band = NULL,
                    diet_tags = ARRAY[]::TEXT[],
                    allergen_tags = ARRAY[]::TEXT[],
                    cuisines = CASE
                        WHEN cuisine IS NOT NULL THEN ARRAY[cuisine]
                        ELSE ARRAY[]::TEXT[]
                    END,
                    meal_types = ARRAY[]::TEXT[],
                    dish_types = ARRAY[]::TEXT[],
                    texture = ARRAY[]::TEXT[],
                    prep_time_min = prep_time_minutes,
                    cook_time_min = cook_time_minutes,
                    total_time_min = CASE
                        WHEN prep_time_minutes IS NOT NULL
                            OR cook_time_minutes IS NOT NULL
                        THEN COALESCE(prep_time_minutes, 0)
                            + COALESCE(cook_time_minutes, 0)
                        ELSE NULL
                    END,
                    passive_time_min = NULL,
                    prep_steps = '[]'::jsonb,
                    estimated_cost_per_serving = NULL,
                    popularity_score = NULL,
                    side_category = NULL,
                    meal_role = NULL,
                    dish_family = NULL,
                    health_tags = ARRAY[]::TEXT[],
                    efficiency_tags = ARRAY[]::TEXT[],
                    experience_tags = ARRAY[]::TEXT[],
                    cost_tier = NULL,
                    festival_tags = ARRAY[]::TEXT[],
                    owner_code = NULL,
                    owner_name = NULL,
                    source = NULL,
                    created_by = NULL,
                    state = CASE
                        WHEN state_method = 'provided_state' THEN state
                        ELSE NULL
                    END,
                    region = CASE
                        WHEN state_method = 'provided_state' THEN region
                        ELSE NULL
                    END,
                    state_confidence = CASE
                        WHEN state_method = 'provided_state'
                        THEN state_confidence
                        ELSE NULL
                    END,
                    state_method = CASE
                        WHEN state_method = 'provided_state'
                        THEN state_method
                        ELSE NULL
                    END,
                    youtube_url = CASE
                        WHEN source_type = 'youtube' THEN source_url
                        ELSE NULL
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """
            )
        )

        counts = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE source_type = 'youtube') AS youtube_rows,
                    COUNT(*) FILTER (WHERE youtube_url IS NOT NULL) AS youtube_urls,
                    COUNT(*) FILTER (
                        WHERE servings IS NOT NULL
                    ) AS source_servings,
                    COUNT(*) FILTER (
                        WHERE prep_time_min IS NOT NULL
                    ) AS source_prep_times,
                    COUNT(*) FILTER (
                        WHERE cook_time_min IS NOT NULL
                    ) AS source_cook_times,
                    COUNT(*) FILTER (
                        WHERE state_method = 'provided_state'
                    ) AS source_state_rows,
                    COUNT(*) FILTER (
                        WHERE jsonb_array_length(ingredients_json) > 0
                    ) AS ingredients_json_rows,
                    COUNT(*) FILTER (
                        WHERE jsonb_array_length(cook_steps) > 0
                    ) AS cook_steps_rows
                FROM recipes
                """
            )
        ).mappings().one()

    return {
        "updated": result.rowcount,
        **dict(counts),
    }


def main():
    print(json.dumps(clear_inferred_fields(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
