CREATE TABLE IF NOT EXISTS recipe_source_tracking (

    source_track_id SERIAL PRIMARY KEY,

    run_id INTEGER,

    recipe_id INTEGER REFERENCES recipes(recipe_id),

    source_name VARCHAR(255),

    source_url TEXT,

    source_url_hash CHAR(64),

    content_hash CHAR(64),

    source_type VARCHAR(50),

    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


ALTER TABLE recipe_source_tracking

ADD COLUMN IF NOT EXISTS run_id INTEGER;


ALTER TABLE recipe_source_tracking

ADD COLUMN IF NOT EXISTS source_url_hash CHAR(64);


ALTER TABLE recipe_source_tracking

ADD COLUMN IF NOT EXISTS content_hash CHAR(64);


CREATE UNIQUE INDEX IF NOT EXISTS ux_recipe_source_tracking_recipe_source

ON recipe_source_tracking(recipe_id, source_name)

WHERE recipe_id IS NOT NULL AND source_name IS NOT NULL;


CREATE TABLE IF NOT EXISTS ingestion_runs (

    run_id SERIAL PRIMARY KEY,

    source_id VARCHAR(255),

    source_name VARCHAR(255),

    source_type VARCHAR(50),

    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',

    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ended_at TIMESTAMP,

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
