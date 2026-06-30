CREATE TABLE IF NOT EXISTS recipes (

    recipe_id SERIAL PRIMARY KEY,

    title TEXT NOT NULL,

    description TEXT,

    cuisine VARCHAR(100),

    state VARCHAR(100),

    region VARCHAR(100),

    state_confidence FLOAT,

    state_method VARCHAR(100),

    prep_time_minutes INT,

    cook_time_minutes INT,

    servings INT,

    source_type VARCHAR(50),

    source_url TEXT,

    source_url_hash CHAR(64),

    content_hash CHAR(64),

    language VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



ALTER TABLE recipes

ADD COLUMN IF NOT EXISTS source_url_hash CHAR(64);


ALTER TABLE recipes

ADD COLUMN IF NOT EXISTS content_hash CHAR(64);


ALTER TABLE recipes

ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;


ALTER TABLE recipes

ADD COLUMN IF NOT EXISTS state VARCHAR(100);


ALTER TABLE recipes

ADD COLUMN IF NOT EXISTS region VARCHAR(100);


ALTER TABLE recipes

ADD COLUMN IF NOT EXISTS state_confidence FLOAT;


ALTER TABLE recipes

ADD COLUMN IF NOT EXISTS state_method VARCHAR(100);


CREATE INDEX IF NOT EXISTS ix_recipes_state_region

ON recipes(state, region);


CREATE UNIQUE INDEX IF NOT EXISTS ux_recipes_source_url_hash

ON recipes(source_url_hash)

WHERE source_url_hash IS NOT NULL;


CREATE UNIQUE INDEX IF NOT EXISTS ux_recipes_content_hash

ON recipes(content_hash)

WHERE content_hash IS NOT NULL;



CREATE TABLE IF NOT EXISTS recipe_sources (

    source_id SERIAL PRIMARY KEY,

    recipe_id INT REFERENCES recipes(recipe_id),

    source_type VARCHAR(50),

    raw_path TEXT,

    metadata JSONB,

    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS recipe_ingredients (

    recipe_ingredient_id SERIAL PRIMARY KEY,

    recipe_id INT REFERENCES recipes(recipe_id),

    ingredient_id INT REFERENCES master_ingredients(ingredient_id),

    quantity FLOAT,

    unit VARCHAR(50),

    preparation TEXT
);


CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_recipe_id

ON recipe_ingredients(recipe_id);


CREATE TABLE IF NOT EXISTS recipe_steps (

    recipe_step_id SERIAL PRIMARY KEY,

    recipe_id INT REFERENCES recipes(recipe_id),

    step_number INT,

    instruction TEXT

);


CREATE UNIQUE INDEX IF NOT EXISTS ux_recipe_steps_recipe_step

ON recipe_steps(recipe_id, step_number);
