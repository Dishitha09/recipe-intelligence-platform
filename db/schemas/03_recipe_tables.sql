CREATE TABLE IF NOT EXISTS recipes (

    recipe_id SERIAL PRIMARY KEY,

    title TEXT NOT NULL,

    description TEXT,

    cuisine VARCHAR(100),

    prep_time_minutes INT,

    cook_time_minutes INT,

    servings INT,

    source_type VARCHAR(50),

    source_url TEXT,

    language VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



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
CREATE TABLE IF NOT EXISTS recipe_steps (

    recipe_step_id SERIAL PRIMARY KEY,

    recipe_id INT REFERENCES recipes(recipe_id),

    step_number INT,

    instruction TEXT

);