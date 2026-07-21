CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS master_ingredients (
    ingredient_id INTEGER PRIMARY KEY,
    canonical_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100),
    default_unit VARCHAR(50),
    density_g_per_ml FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE SEQUENCE IF NOT EXISTS master_ingredients_ingredient_id_seq
OWNED BY master_ingredients.ingredient_id;

ALTER TABLE master_ingredients
ALTER COLUMN ingredient_id
SET DEFAULT nextval('master_ingredients_ingredient_id_seq');

CREATE TABLE IF NOT EXISTS ingredient_aliases (
    alias_id INTEGER PRIMARY KEY,
    ingredient_id INTEGER REFERENCES master_ingredients(ingredient_id),
    alias_name VARCHAR(255) NOT NULL,
    language VARCHAR(50),
    source VARCHAR(100)
);

CREATE SEQUENCE IF NOT EXISTS ingredient_aliases_alias_id_seq
OWNED BY ingredient_aliases.alias_id;

ALTER TABLE ingredient_aliases
ALTER COLUMN alias_id
SET DEFAULT nextval('ingredient_aliases_alias_id_seq');

CREATE UNIQUE INDEX IF NOT EXISTS idx_ingredient_aliases_alias_lower
ON ingredient_aliases (LOWER(alias_name));

CREATE INDEX IF NOT EXISTS idx_ingredient_aliases_ingredient_id
ON ingredient_aliases (ingredient_id);

CREATE INDEX IF NOT EXISTS idx_master_ingredients_canonical_name
ON master_ingredients (canonical_name);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id SERIAL PRIMARY KEY,
    source_id VARCHAR(255),
    source_name VARCHAR(255),
    source_type VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    records_found INTEGER DEFAULT 0,
    records_coerced INTEGER DEFAULT 0,
    records_accepted INTEGER DEFAULT 0,
    records_review INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    records_loaded INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    summary JSONB DEFAULT '{}'::jsonb,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_ingestion_runs_source_status
ON ingestion_runs(source_id, status, started_at DESC);

CREATE TABLE IF NOT EXISTS validation_reports (
    validation_id SERIAL PRIMARY KEY,
    recipe_id UUID REFERENCES recipe_catalogue_v3(recipe_id),
    status VARCHAR(50),
    validation_message TEXT,
    failure_codes JSONB DEFAULT '[]'::jsonb,
    check_results JSONB,
    flags JSONB DEFAULT '[]'::jsonb,
    summary JSONB DEFAULT '{}'::jsonb,
    report_hash CHAR(64),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_validation_reports_report_hash
ON validation_reports(report_hash)
WHERE report_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_validation_reports_report_hash_full
ON validation_reports(report_hash);

CREATE INDEX IF NOT EXISTS ix_validation_reports_recipe_status
ON validation_reports(recipe_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_validation_reports_failure_codes
ON validation_reports USING GIN(failure_codes);

CREATE TABLE IF NOT EXISTS review_queue (
    review_id SERIAL PRIMARY KEY,
    recipe_id UUID REFERENCES recipe_catalogue_v3(recipe_id),
    record_id UUID,
    reason TEXT,
    reason_codes JSONB DEFAULT '[]'::jsonb,
    validation_report JSONB,
    review_hash CHAR(64),
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_review_queue_review_hash
ON review_queue(review_hash)
WHERE review_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_review_queue_review_hash_full
ON review_queue(review_hash);

CREATE INDEX IF NOT EXISTS ix_review_queue_reason_codes
ON review_queue USING GIN(reason_codes);

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    dlq_id SERIAL PRIMARY KEY,
    source_type VARCHAR(50),
    record_id UUID,
    recipe_id UUID REFERENCES recipe_catalogue_v3(recipe_id),
    raw_payload JSONB,
    error_message TEXT,
    reason_code VARCHAR(100),
    reason_codes JSONB DEFAULT '[]'::jsonb,
    validation_report JSONB,
    dead_letter_hash CHAR(64),
    failed_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_dead_letter_queue_hash
ON dead_letter_queue(dead_letter_hash)
WHERE dead_letter_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_dead_letter_queue_hash_full
ON dead_letter_queue(dead_letter_hash);

CREATE INDEX IF NOT EXISTS ix_dead_letter_queue_reason_codes
ON dead_letter_queue USING GIN(reason_codes);

CREATE TABLE IF NOT EXISTS ingredient_resolution_reports (
    resolution_id SERIAL PRIMARY KEY,
    recipe_id UUID REFERENCES recipe_catalogue_v3(recipe_id),
    source_position INTEGER,
    raw_name TEXT,
    normalized_name TEXT,
    canonical_name TEXT,
    master_ingredient_id INTEGER REFERENCES master_ingredients(ingredient_id),
    method TEXT,
    tier TEXT,
    confidence_score FLOAT,
    enrichment_flags JSONB DEFAULT '[]'::jsonb,
    report_hash CHAR(64),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_ingredient_resolution_reports_hash
ON ingredient_resolution_reports(report_hash)
WHERE report_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_ingredient_resolution_reports_hash_full
ON ingredient_resolution_reports(report_hash);

CREATE INDEX IF NOT EXISTS ix_ingredient_resolution_reports_recipe
ON ingredient_resolution_reports(recipe_id);

CREATE INDEX IF NOT EXISTS ix_ingredient_resolution_reports_tier
ON ingredient_resolution_reports(tier);

DO $$
BEGIN
    IF to_regtype('vector') IS NOT NULL THEN
        CREATE TABLE IF NOT EXISTS ingredient_embeddings (
            embedding_id SERIAL PRIMARY KEY,
            ingredient_id INTEGER REFERENCES master_ingredients(ingredient_id),
            embedding VECTOR(384),
            created_at TIMESTAMPTZ DEFAULT now()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS ux_ingredient_embeddings_ingredient_id
        ON ingredient_embeddings(ingredient_id);

        BEGIN
            CREATE INDEX IF NOT EXISTS idx_ingredient_embeddings_hnsw
            ON ingredient_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN
                RAISE NOTICE 'Skipping ingredient_embeddings HNSW index because this pgvector version does not support hnsw.';
        END;

        CREATE TABLE IF NOT EXISTS recipe_embeddings (
            embedding_id SERIAL PRIMARY KEY,
            recipe_id UUID REFERENCES recipe_catalogue_v3(recipe_id),
            embedding VECTOR(384),
            created_at TIMESTAMPTZ DEFAULT now()
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
        RAISE NOTICE 'Skipping vector-backed v3 embedding tables because pgvector is unavailable.';
    END IF;
END $$;
