CREATE TABLE IF NOT EXISTS recipe_reviews (

    review_id SERIAL PRIMARY KEY,

    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,

    user_name VARCHAR(255) NOT NULL DEFAULT 'anonymous',

    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),

    review_text TEXT,

    source VARCHAR(100) DEFAULT 'web',

    review_hash CHAR(64) NOT NULL UNIQUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS ix_recipe_reviews_recipe_id

ON recipe_reviews(recipe_id);


CREATE TABLE IF NOT EXISTS recipe_ratings_summary (

    recipe_id INTEGER PRIMARY KEY REFERENCES recipes(recipe_id) ON DELETE CASCADE,

    review_count INTEGER NOT NULL DEFAULT 0,

    average_rating NUMERIC(3, 2) NOT NULL DEFAULT 0,

    five_star_count INTEGER NOT NULL DEFAULT 0,

    four_star_count INTEGER NOT NULL DEFAULT 0,

    three_star_count INTEGER NOT NULL DEFAULT 0,

    two_star_count INTEGER NOT NULL DEFAULT 0,

    one_star_count INTEGER NOT NULL DEFAULT 0,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE OR REPLACE FUNCTION refresh_recipe_ratings_summary()

RETURNS TRIGGER AS $$
DECLARE
    changed_recipe_id INTEGER;
BEGIN
    changed_recipe_id := COALESCE(NEW.recipe_id, OLD.recipe_id);

    INSERT INTO recipe_ratings_summary
        (
            recipe_id,
            review_count,
            average_rating,
            five_star_count,
            four_star_count,
            three_star_count,
            two_star_count,
            one_star_count,
            updated_at
        )
    SELECT
        changed_recipe_id,
        COUNT(*)::integer,
        COALESCE(ROUND(AVG(rating)::numeric, 2), 0),
        COUNT(*) FILTER (WHERE rating = 5)::integer,
        COUNT(*) FILTER (WHERE rating = 4)::integer,
        COUNT(*) FILTER (WHERE rating = 3)::integer,
        COUNT(*) FILTER (WHERE rating = 2)::integer,
        COUNT(*) FILTER (WHERE rating = 1)::integer,
        CURRENT_TIMESTAMP
    FROM recipe_reviews
    WHERE recipe_id = changed_recipe_id
    ON CONFLICT (recipe_id)
    DO UPDATE SET
        review_count = EXCLUDED.review_count,
        average_rating = EXCLUDED.average_rating,
        five_star_count = EXCLUDED.five_star_count,
        four_star_count = EXCLUDED.four_star_count,
        three_star_count = EXCLUDED.three_star_count,
        two_star_count = EXCLUDED.two_star_count,
        one_star_count = EXCLUDED.one_star_count,
        updated_at = CURRENT_TIMESTAMP;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trg_recipe_reviews_refresh_summary

ON recipe_reviews;


CREATE TRIGGER trg_recipe_reviews_refresh_summary

AFTER INSERT OR UPDATE OR DELETE ON recipe_reviews

FOR EACH ROW EXECUTE FUNCTION refresh_recipe_ratings_summary();


CREATE TABLE IF NOT EXISTS trending_recipes (

    recipe_id INTEGER PRIMARY KEY REFERENCES recipes(recipe_id) ON DELETE CASCADE,

    trending_score NUMERIC(10, 4) NOT NULL DEFAULT 0,

    reason TEXT,

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS ix_trending_recipes_score

ON trending_recipes(trending_score DESC);


CREATE TABLE IF NOT EXISTS pipeline_audit_log (

    audit_id SERIAL PRIMARY KEY,

    run_id INTEGER REFERENCES ingestion_runs(run_id),

    recipe_id INTEGER REFERENCES recipes(recipe_id) ON DELETE SET NULL,

    source_name VARCHAR(255),

    source_type VARCHAR(50),

    source_url TEXT,

    validation_status VARCHAR(50),

    event_type VARCHAR(100) NOT NULL DEFAULT 'ingestion',

    ps_checks JSONB DEFAULT '{}'::jsonb,

    details JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS ix_pipeline_audit_log_run_id

ON pipeline_audit_log(run_id);


CREATE INDEX IF NOT EXISTS ix_pipeline_audit_log_recipe_id

ON pipeline_audit_log(recipe_id);


CREATE INDEX IF NOT EXISTS ix_pipeline_audit_log_status

ON pipeline_audit_log(validation_status, event_type);
