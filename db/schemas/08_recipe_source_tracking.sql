CREATE TABLE IF NOT EXISTS recipe_source_tracking (

    source_track_id SERIAL PRIMARY KEY,

    recipe_id INTEGER REFERENCES recipes(recipe_id),

    source_name VARCHAR(255),

    source_url TEXT,

    source_type VARCHAR(50),

    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);