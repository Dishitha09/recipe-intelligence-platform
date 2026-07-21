DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'recipe_steps'
          AND column_name = 'step_id'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'recipe_steps'
          AND column_name = 'recipe_step_id'
    ) THEN
        ALTER TABLE recipe_steps
        RENAME COLUMN step_id TO recipe_step_id;
    END IF;
END $$;


ALTER TABLE recipe_steps

ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;


CREATE UNIQUE INDEX IF NOT EXISTS ux_recipe_steps_recipe_step

ON recipe_steps(recipe_id, step_number);
