CREATE TABLE IF NOT EXISTS recipe_variations (

    variation_id SERIAL PRIMARY KEY,

    canonical_recipe_id INTEGER REFERENCES recipes(recipe_id),

    recipe_id INTEGER REFERENCES recipes(recipe_id),

    variation_name VARCHAR(255),

    variation_type VARCHAR(100),

    source VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);
