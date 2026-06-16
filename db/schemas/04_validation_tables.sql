CREATE TABLE IF NOT EXISTS validation_reports (

    validation_id SERIAL PRIMARY KEY,

    recipe_id INT,

    status VARCHAR(50),

    validation_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS review_queue (

    review_id SERIAL PRIMARY KEY,

    recipe_id INT,

    reason TEXT,

    status VARCHAR(50) DEFAULT 'PENDING',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS dead_letter_queue (

    dlq_id SERIAL PRIMARY KEY,

    source_type VARCHAR(50),

    raw_payload JSONB,

    error_message TEXT,

    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);