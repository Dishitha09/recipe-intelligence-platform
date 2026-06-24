DO $$
BEGIN
    IF to_regtype('vector') IS NOT NULL THEN
        CREATE TABLE IF NOT EXISTS recipe_embeddings (

            embedding_id SERIAL PRIMARY KEY,

            recipe_id INTEGER REFERENCES recipes(recipe_id),

            embedding VECTOR(384),

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );
    ELSE
        RAISE NOTICE 'Skipping recipe_embeddings because pgvector is unavailable.';
    END IF;
END $$;
