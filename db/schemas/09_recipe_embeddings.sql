CREATE TABLE IF NOT EXISTS recipe_embeddings (

    embedding_id SERIAL PRIMARY KEY,

    recipe_id INTEGER REFERENCES recipes(recipe_id),

    embedding VECTOR(384),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);