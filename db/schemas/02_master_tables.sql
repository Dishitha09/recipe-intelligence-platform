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


CREATE UNIQUE INDEX IF NOT EXISTS idx_ingredient_aliases_alias_lower
ON ingredient_aliases (LOWER(alias_name));


CREATE INDEX IF NOT EXISTS idx_ingredient_aliases_ingredient_id
ON ingredient_aliases (ingredient_id);



CREATE INDEX IF NOT EXISTS idx_master_ingredients_canonical_name
ON master_ingredients (canonical_name);


DO $$
BEGIN
    IF to_regtype('vector') IS NOT NULL THEN
        CREATE TABLE IF NOT EXISTS ingredient_embeddings (

            embedding_id SERIAL PRIMARY KEY,

            ingredient_id INT REFERENCES master_ingredients(ingredient_id),

            embedding VECTOR(384)
        );

        CREATE INDEX IF NOT EXISTS idx_ingredient_embeddings_ivfflat
        ON ingredient_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);

        BEGIN
            CREATE INDEX IF NOT EXISTS idx_ingredient_embeddings_hnsw
            ON ingredient_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN
                RAISE NOTICE 'Skipping ingredient_embeddings HNSW index because this pgvector version does not support hnsw.';
        END;
    ELSE
        RAISE NOTICE 'Skipping ingredient_embeddings because pgvector is unavailable.';
    END IF;
END $$;
