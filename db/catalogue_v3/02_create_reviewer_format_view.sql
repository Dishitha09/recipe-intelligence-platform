CREATE OR REPLACE VIEW recipe_catalogue_v3_reviewer_format AS
SELECT
    r.name,
    r.course,
    r.region,
    r.cuisines,
    r.meal_types,
    COALESCE(
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'item',
                    NULLIF(
                        btrim(
                            regexp_replace(
                                regexp_replace(
                                    base_ingredient.item_text,
                                    '^\s*(?:\d+(?:-\d+/\d+)?(?:\.\d+)?|\d+/\d+|\d+\s+\d+/\d+|\d+\s+to\s+\d+(?:\.\d+)?)\s*(?:cups?|teaspoons?|tablespoons?|tbsp|tsp|grams?|gram|g|kg|ml|milliliters?|millilitres?|ounces?|ounce|oz|pounds?|pound|lb|lbs|cloves?|pieces?|slices?|sprigs?|inch|inches)?\s*',
                                    '',
                                    'i'
                                ),
                                '\s+-\s+.*$',
                                '',
                                'i'
                            )
                        ),
                        ''
                    ),
                    'quantity',
                    CASE
                        WHEN ingredient ? 'canonical_quantity'
                             AND jsonb_typeof(ingredient->'canonical_quantity') = 'number'
                        THEN ingredient->'canonical_quantity'
                        WHEN ingredient ? 'quantity'
                             AND jsonb_typeof(ingredient->'quantity') = 'number'
                        THEN ingredient->'quantity'
                        ELSE 'null'::jsonb
                    END,
                    'unit',
                    CASE
                        WHEN NULLIF(ingredient->>'canonical_unit', '') IS NOT NULL
                        THEN to_jsonb(ingredient->>'canonical_unit')
                        WHEN NULLIF(ingredient->>'unit', '') IS NOT NULL
                        THEN to_jsonb(ingredient->>'unit')
                        ELSE 'null'::jsonb
                    END,
                    'prep',
                    to_jsonb(base_ingredient.prep_text)
                )
                ORDER BY COALESCE((ingredient->>'source_position')::integer, 999999)
            )
            FROM jsonb_array_elements(r.ingredients_json) AS ingredient
            CROSS JOIN LATERAL (
                SELECT
                    COALESCE(
                        ingredient->>'name',
                        ingredient->>'item',
                        ingredient->>'raw_text'
                    ) AS item_text,
                    COALESCE(
                        NULLIF(ingredient->>'prep', ''),
                        NULLIF(ingredient->>'preparation', ''),
                        NULLIF(
                            btrim(
                                substring(
                                    COALESCE(
                                        ingredient->>'name',
                                        ingredient->>'item',
                                        ingredient->>'raw_text'
                                    )
                                    from '\s+-\s+(.*)$'
                                )
                            ),
                            ''
                        )
                    ) AS prep_text
            ) AS base_ingredient
        ),
        '[]'::jsonb
    ) AS ingredients_json,
    r.description,
    r.servings,
    r.difficulty_level,
    r.youtube_url,
    r.image_url,
    r.prep_steps,
    r.cook_steps,
    r.quick_steps,
    r.nutrition_info,
    r.tags,
    r.metadata,
    r.diet,
    r.complexity,
    r.spice_level,
    r.budget_band,
    r.dish_types,
    r.texture,
    r.diet_tags,
    r.allergen_tags,
    r.health_tags,
    r.efficiency_tags,
    r.experience_tags,
    r.cost_tier,
    r.side_category,
    r.dish_family,
    r.festival_tags,
    r.prep_time_min,
    r.cook_time_min,
    r.total_time_min,
    r.passive_time_min,
    r.estimated_cost_per_serving,
    r.popularity_score,
    r.owner_code,
    r.owner_name,
    r.source,
    r.language,
    r.is_public,
    r.created_by,
    r.is_active,
    r.meal_role,
    r.created_at,
    r.updated_at
FROM recipe_catalogue_v3 r;
