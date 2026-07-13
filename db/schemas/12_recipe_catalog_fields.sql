ALTER TABLE recipes
ADD COLUMN IF NOT EXISTS name TEXT;

UPDATE recipes
SET name = title
WHERE name IS NULL;

ALTER TABLE recipes
ADD COLUMN IF NOT EXISTS nutrition_info JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS difficulty_level VARCHAR(20) DEFAULT 'MEDIUM',
ADD COLUMN IF NOT EXISTS youtube_url TEXT,
ADD COLUMN IF NOT EXISTS image_url TEXT,
ADD COLUMN IF NOT EXISTS course TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS diet VARCHAR(50),
ADD COLUMN IF NOT EXISTS spice_level VARCHAR(50),
ADD COLUMN IF NOT EXISTS complexity VARCHAR(50),
ADD COLUMN IF NOT EXISTS budget_band VARCHAR(50),
ADD COLUMN IF NOT EXISTS diet_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS allergen_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS cuisines TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS meal_types TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS dish_types TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS texture TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS prep_time_min INTEGER,
ADD COLUMN IF NOT EXISTS cook_time_min INTEGER,
ADD COLUMN IF NOT EXISTS total_time_min INTEGER,
ADD COLUMN IF NOT EXISTS passive_time_min INTEGER,
ADD COLUMN IF NOT EXISTS ingredients_json JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS prep_steps JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS cook_steps JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS quick_steps JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS estimated_cost_per_serving NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS popularity_score NUMERIC(10, 4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS side_category VARCHAR(100),
ADD COLUMN IF NOT EXISTS meal_role VARCHAR(100),
ADD COLUMN IF NOT EXISTS dish_family VARCHAR(100),
ADD COLUMN IF NOT EXISTS health_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS efficiency_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS experience_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS cost_tier VARCHAR(50),
ADD COLUMN IF NOT EXISTS festival_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS owner_code VARCHAR(100),
ADD COLUMN IF NOT EXISTS owner_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS source TEXT,
ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS created_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

UPDATE recipes
SET
    prep_time_min = prep_time_minutes,
    cook_time_min = cook_time_minutes,
    total_time_min = CASE
        WHEN prep_time_minutes IS NOT NULL OR cook_time_minutes IS NOT NULL
        THEN COALESCE(prep_time_minutes, 0) + COALESCE(cook_time_minutes, 0)
        ELSE NULL
    END,
    cuisines = CASE
        WHEN cuisine IS NOT NULL
        THEN ARRAY[cuisine]
        ELSE ARRAY[]::TEXT[]
    END,
    metadata = COALESCE(metadata, '{}'::jsonb)
        || jsonb_build_object(
            'legacy_source_type', source_type,
            'state', state,
            'region', region,
            'state_confidence', state_confidence,
            'state_method', state_method
        )
WHERE
    metadata IS NULL
    OR cuisines IS NULL
    OR prep_time_min IS DISTINCT FROM prep_time_minutes
    OR cook_time_min IS DISTINCT FROM cook_time_minutes;

UPDATE recipes r
SET ingredients_json = COALESCE(i.ingredients_json, '[]'::jsonb)
FROM (
    SELECT
        recipe_id,
        jsonb_agg(
            jsonb_build_object(
                'ingredient_name', ingredient_name,
                'quantity', quantity,
                'unit', unit,
                'canonical_name', canonical_name,
                'canonical_quantity', canonical_quantity,
                'canonical_unit', canonical_unit,
                'preparation', preparation
            )
            ORDER BY recipe_ingredient_id
        ) AS ingredients_json
    FROM recipe_ingredients
    GROUP BY recipe_id
) i
WHERE r.recipe_id = i.recipe_id;

UPDATE recipes r
SET cook_steps = COALESCE(s.cook_steps, '[]'::jsonb)
FROM (
    SELECT
        recipe_id,
        jsonb_agg(
            jsonb_build_object(
                'step_number', step_number,
                'instruction', instruction
            )
            ORDER BY step_number
        ) AS cook_steps
    FROM recipe_steps
    GROUP BY recipe_id
) s
WHERE r.recipe_id = s.recipe_id;

UPDATE recipes r
SET quick_steps = COALESCE(s.quick_steps, '[]'::jsonb)
FROM (
    SELECT
        recipe_id,
        jsonb_agg(to_jsonb(instruction) ORDER BY step_number) AS quick_steps
    FROM (
        SELECT
            recipe_id,
            step_number,
            instruction,
            ROW_NUMBER() OVER (
                PARTITION BY recipe_id
                ORDER BY step_number
            ) AS step_rank
        FROM recipe_steps
    ) ranked_steps
    WHERE step_rank <= 5
    GROUP BY recipe_id
) s
WHERE r.recipe_id = s.recipe_id;

CREATE OR REPLACE FUNCTION set_recipe_catalog_defaults()
RETURNS TRIGGER AS $$
BEGIN
    NEW.name := COALESCE(NULLIF(NEW.name, ''), NEW.title);
    NEW.is_public := COALESCE(NEW.is_public, FALSE);
    NEW.is_active := COALESCE(NEW.is_active, TRUE);
    NEW.updated_at := CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recipes_catalog_defaults
ON recipes;

CREATE TRIGGER trg_recipes_catalog_defaults
BEFORE INSERT OR UPDATE ON recipes
FOR EACH ROW EXECUTE FUNCTION set_recipe_catalog_defaults();

ALTER TABLE recipes
ALTER COLUMN name SET NOT NULL,
ALTER COLUMN servings DROP DEFAULT,
ALTER COLUMN servings DROP NOT NULL,
ALTER COLUMN language DROP DEFAULT,
ALTER COLUMN is_public SET DEFAULT FALSE,
ALTER COLUMN is_active SET DEFAULT TRUE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_recipes_difficulty_level'
    ) THEN
        ALTER TABLE recipes
        ADD CONSTRAINT ck_recipes_difficulty_level
        CHECK (
            difficulty_level IS NULL
            OR difficulty_level IN ('EASY', 'MEDIUM', 'HARD', 'EXPERT')
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_recipes_cost_tier'
    ) THEN
        ALTER TABLE recipes
        ADD CONSTRAINT ck_recipes_cost_tier
        CHECK (
            cost_tier IS NULL
            OR cost_tier IN ('BUDGET', 'MID_RANGE', 'PREMIUM')
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_recipes_name_trgm
ON recipes USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_recipes_diet
ON recipes(diet);

CREATE INDEX IF NOT EXISTS ix_recipes_course_gin
ON recipes USING gin(course);

CREATE INDEX IF NOT EXISTS ix_recipes_tags_gin
ON recipes USING gin(tags);

CREATE INDEX IF NOT EXISTS ix_recipes_diet_tags_gin
ON recipes USING gin(diet_tags);

CREATE INDEX IF NOT EXISTS ix_recipes_allergen_tags_gin
ON recipes USING gin(allergen_tags);

CREATE INDEX IF NOT EXISTS ix_recipes_cuisines_gin
ON recipes USING gin(cuisines);

CREATE INDEX IF NOT EXISTS ix_recipes_meal_types_gin
ON recipes USING gin(meal_types);

CREATE INDEX IF NOT EXISTS ix_recipes_dish_types_gin
ON recipes USING gin(dish_types);

CREATE INDEX IF NOT EXISTS ix_recipes_health_tags_gin
ON recipes USING gin(health_tags);

CREATE INDEX IF NOT EXISTS ix_recipes_efficiency_tags_gin
ON recipes USING gin(efficiency_tags);

CREATE INDEX IF NOT EXISTS ix_recipes_experience_tags_gin
ON recipes USING gin(experience_tags);

CREATE INDEX IF NOT EXISTS ix_recipes_festival_tags_gin
ON recipes USING gin(festival_tags);

CREATE INDEX IF NOT EXISTS ix_recipes_active_public
ON recipes(is_active, is_public);

DROP VIEW IF EXISTS recipe_source_truth_catalog;
DROP VIEW IF EXISTS recipe_catalog_app;

CREATE OR REPLACE VIEW recipe_catalog_app AS
SELECT
    r.recipe_id,
    r.name,
    r.title,
    r.description,
    r.youtube_url,
    r.image_url,
    r.servings,
    r.prep_time_min,
    r.cook_time_min,
    r.total_time_min,
    r.cuisine,
    r.cuisines,
    r.state,
    r.region,
    r.ingredients_json,
    r.cook_steps,
    r.source_url,
    r.source_type,
    r.language,
    r.created_at,
    r.updated_at
FROM recipes r;

CREATE OR REPLACE VIEW recipe_source_truth_catalog AS
SELECT *
FROM recipe_catalog_app;
