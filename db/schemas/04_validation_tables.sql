CREATE TABLE IF NOT EXISTS validation_reports (

    validation_id SERIAL PRIMARY KEY,

    recipe_id INT,

    status VARCHAR(50),

    validation_message TEXT,

    check_results JSONB,

    flags JSONB DEFAULT '[]'::jsonb,

    summary JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS review_queue (

    review_id SERIAL PRIMARY KEY,

    recipe_id INT,

    record_id UUID,

    reason TEXT,

    validation_report JSONB,

    status VARCHAR(50) DEFAULT 'PENDING',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS dead_letter_queue (

    dlq_id SERIAL PRIMARY KEY,

    source_type VARCHAR(50),

    record_id UUID,

    raw_payload JSONB,

    error_message TEXT,

    validation_report JSONB,

    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
