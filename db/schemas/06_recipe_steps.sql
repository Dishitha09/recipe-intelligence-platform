CREATE TABLE IF NOT EXISTS recipe_steps (

    step_id SERIAL PRIMARY KEY,

    recipe_id INTEGER REFERENCES recipes(recipe_id),

    step_number INTEGER NOT NULL,

    instruction TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);