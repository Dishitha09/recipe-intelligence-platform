ALTER TABLE recipe_steps

ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;


CREATE UNIQUE INDEX IF NOT EXISTS ux_recipe_steps_recipe_step

ON recipe_steps(recipe_id, step_number);
