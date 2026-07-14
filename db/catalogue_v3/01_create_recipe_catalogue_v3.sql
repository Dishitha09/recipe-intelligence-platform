CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION catalogue_v3_text_array_is_uppercase(values TEXT[])
RETURNS BOOLEAN
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT COALESCE(
        bool_and(value = upper(value)),
        TRUE
    )
    FROM unnest(values) AS value
    WHERE value IS NOT NULL AND value <> ''
$$;

CREATE OR REPLACE FUNCTION catalogue_v3_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS recipe_catalogue_v3 (
    recipe_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    description TEXT,
    nutrition_info JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    servings INTEGER NOT NULL,
    difficulty_level TEXT,
    youtube_url TEXT,
    image_url TEXT,
    course TEXT[] DEFAULT ARRAY[]::TEXT[],
    region TEXT,
    diet TEXT,
    spice_level TEXT,
    complexity TEXT,
    budget_band TEXT,
    diet_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    allergen_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    cuisines TEXT[] DEFAULT ARRAY[]::TEXT[],
    meal_types TEXT[] DEFAULT ARRAY[]::TEXT[],
    dish_types TEXT[] DEFAULT ARRAY[]::TEXT[],
    texture TEXT[] DEFAULT ARRAY[]::TEXT[],

    prep_time_min INTEGER,
    cook_time_min INTEGER,
    total_time_min INTEGER,
    passive_time_min INTEGER,

    ingredients_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    prep_steps JSONB DEFAULT '[]'::jsonb,
    cook_steps JSONB DEFAULT '[]'::jsonb,
    quick_steps TEXT[] DEFAULT ARRAY[]::TEXT[],

    estimated_cost_per_serving NUMERIC(10,2),
    popularity_score NUMERIC(10,4) DEFAULT 0,

    side_category TEXT,
    meal_role TEXT,
    dish_family TEXT,
    health_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    efficiency_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    experience_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    cost_tier TEXT,
    festival_tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    owner_code TEXT,
    owner_name TEXT,
    source TEXT,
    language TEXT DEFAULT 'en',
    is_public BOOLEAN DEFAULT false,
    created_by TEXT DEFAULT 'system_seed',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT recipe_catalogue_v3_name_trim_len_chk
        CHECK (length(trim(name)) > 2),
    CONSTRAINT recipe_catalogue_v3_servings_positive_chk
        CHECK (servings > 0),
    CONSTRAINT recipe_catalogue_v3_difficulty_chk
        CHECK (
            difficulty_level IS NULL
            OR difficulty_level IN ('EASY', 'MEDIUM', 'HARD', 'EXPERT')
        ),
    CONSTRAINT recipe_catalogue_v3_diet_lowercase_chk
        CHECK (diet IS NULL OR diet = lower(diet)),
    CONSTRAINT recipe_catalogue_v3_diet_tags_uppercase_chk
        CHECK (catalogue_v3_text_array_is_uppercase(diet_tags)),
    CONSTRAINT recipe_catalogue_v3_allergen_tags_uppercase_chk
        CHECK (catalogue_v3_text_array_is_uppercase(allergen_tags)),
    CONSTRAINT recipe_catalogue_v3_health_tags_uppercase_chk
        CHECK (catalogue_v3_text_array_is_uppercase(health_tags)),
    CONSTRAINT recipe_catalogue_v3_efficiency_tags_uppercase_chk
        CHECK (catalogue_v3_text_array_is_uppercase(efficiency_tags)),
    CONSTRAINT recipe_catalogue_v3_experience_tags_uppercase_chk
        CHECK (catalogue_v3_text_array_is_uppercase(experience_tags)),
    CONSTRAINT recipe_catalogue_v3_cost_tier_chk
        CHECK (
            cost_tier IS NULL
            OR cost_tier IN ('BUDGET', 'MID_RANGE', 'PREMIUM')
        ),
    CONSTRAINT recipe_catalogue_v3_prep_time_nonnegative_chk
        CHECK (prep_time_min IS NULL OR prep_time_min >= 0),
    CONSTRAINT recipe_catalogue_v3_cook_time_nonnegative_chk
        CHECK (cook_time_min IS NULL OR cook_time_min >= 0),
    CONSTRAINT recipe_catalogue_v3_total_time_nonnegative_chk
        CHECK (total_time_min IS NULL OR total_time_min >= 0),
    CONSTRAINT recipe_catalogue_v3_passive_time_nonnegative_chk
        CHECK (passive_time_min IS NULL OR passive_time_min >= 0),
    CONSTRAINT recipe_catalogue_v3_nutrition_object_chk
        CHECK (jsonb_typeof(nutrition_info) = 'object'),
    CONSTRAINT recipe_catalogue_v3_metadata_object_chk
        CHECK (jsonb_typeof(metadata) = 'object'),
    CONSTRAINT recipe_catalogue_v3_ingredients_array_chk
        CHECK (jsonb_typeof(ingredients_json) = 'array'),
    CONSTRAINT recipe_catalogue_v3_prep_steps_array_chk
        CHECK (jsonb_typeof(prep_steps) = 'array'),
    CONSTRAINT recipe_catalogue_v3_cook_steps_array_chk
        CHECK (jsonb_typeof(cook_steps) = 'array')
);

DROP TRIGGER IF EXISTS trg_recipe_catalogue_v3_updated_at
ON recipe_catalogue_v3;

CREATE TRIGGER trg_recipe_catalogue_v3_updated_at
BEFORE UPDATE ON recipe_catalogue_v3
FOR EACH ROW
EXECUTE FUNCTION catalogue_v3_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_name_trgm
ON recipe_catalogue_v3 USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_tags_gin
ON recipe_catalogue_v3 USING gin (tags);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_course_gin
ON recipe_catalogue_v3 USING gin (course);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_diet_tags_gin
ON recipe_catalogue_v3 USING gin (diet_tags);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_allergen_tags_gin
ON recipe_catalogue_v3 USING gin (allergen_tags);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_cuisines_gin
ON recipe_catalogue_v3 USING gin (cuisines);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_meal_types_gin
ON recipe_catalogue_v3 USING gin (meal_types);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_dish_types_gin
ON recipe_catalogue_v3 USING gin (dish_types);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_health_tags_gin
ON recipe_catalogue_v3 USING gin (health_tags);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_efficiency_tags_gin
ON recipe_catalogue_v3 USING gin (efficiency_tags);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_experience_tags_gin
ON recipe_catalogue_v3 USING gin (experience_tags);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_festival_tags_gin
ON recipe_catalogue_v3 USING gin (festival_tags);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_meal_role
ON recipe_catalogue_v3 (meal_role);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_dish_family
ON recipe_catalogue_v3 (dish_family);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_side_category
ON recipe_catalogue_v3 (side_category);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_diet
ON recipe_catalogue_v3 (diet);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_region
ON recipe_catalogue_v3 (region);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_cost_tier
ON recipe_catalogue_v3 (cost_tier);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_is_active
ON recipe_catalogue_v3 (is_active);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_is_public
ON recipe_catalogue_v3 (is_public);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_source
ON recipe_catalogue_v3 (source);

CREATE INDEX IF NOT EXISTS idx_recipe_catalogue_v3_created_at
ON recipe_catalogue_v3 (created_at);
