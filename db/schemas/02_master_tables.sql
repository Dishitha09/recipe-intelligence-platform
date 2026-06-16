CREATE TABLE IF NOT EXISTS master_ingredients (

    ingredient_id SERIAL PRIMARY KEY,

    canonical_name VARCHAR(255) UNIQUE NOT NULL,

    category VARCHAR(100),

    default_unit VARCHAR(50),

    density_g_per_ml FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS ingredient_aliases (

    alias_id SERIAL PRIMARY KEY,

    ingredient_id INT REFERENCES master_ingredients(ingredient_id),

    alias_name VARCHAR(255) NOT NULL,

    language VARCHAR(50),

    source VARCHAR(100)
);



CREATE TABLE IF NOT EXISTS ingredient_embeddings (

    embedding_id SERIAL PRIMARY KEY,

    ingredient_id INT REFERENCES master_ingredients(ingredient_id),

    embedding VECTOR(1024)
);