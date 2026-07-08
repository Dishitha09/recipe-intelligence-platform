DO $$
BEGIN
    IF to_regtype('vector') IS NOT NULL THEN
        CREATE TABLE IF NOT EXISTS recipe_embeddings (

            embedding_id SERIAL PRIMARY KEY,

            recipe_id INTEGER REFERENCES recipes(recipe_id),

            embedding VECTOR(384),

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );

        CREATE UNIQUE INDEX IF NOT EXISTS ux_recipe_embeddings_recipe_id
        ON recipe_embeddings(recipe_id);

        BEGIN
            CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_hnsw
            ON recipe_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN
                RAISE NOTICE 'Skipping recipe_embeddings HNSW index because this pgvector version does not support hnsw.';
        END;
    ELSE
        RAISE NOTICE 'Skipping recipe_embeddings because pgvector is unavailable.';
    END IF;
END $$;
