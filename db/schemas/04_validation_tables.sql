CREATE TABLE IF NOT EXISTS validation_reports (

    validation_id SERIAL PRIMARY KEY,

    recipe_id INT,

    status VARCHAR(50),

    validation_message TEXT,

    failure_codes JSONB DEFAULT '[]'::jsonb,

    check_results JSONB,

    flags JSONB DEFAULT '[]'::jsonb,

    summary JSONB DEFAULT '{}'::jsonb,

    report_hash CHAR(64),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE validation_reports

ADD COLUMN IF NOT EXISTS failure_codes JSONB DEFAULT '[]'::jsonb;


ALTER TABLE validation_reports

ADD COLUMN IF NOT EXISTS report_hash CHAR(64);


CREATE UNIQUE INDEX IF NOT EXISTS ux_validation_reports_report_hash

ON validation_reports(report_hash)

WHERE report_hash IS NOT NULL;


CREATE INDEX IF NOT EXISTS ix_validation_reports_failure_codes

ON validation_reports USING GIN(failure_codes);



CREATE TABLE IF NOT EXISTS review_queue (

    review_id SERIAL PRIMARY KEY,

    recipe_id INT,

    record_id UUID,

    reason TEXT,

    reason_codes JSONB DEFAULT '[]'::jsonb,

    validation_report JSONB,

    review_hash CHAR(64),

    status VARCHAR(50) DEFAULT 'PENDING',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE review_queue

ADD COLUMN IF NOT EXISTS reason_codes JSONB DEFAULT '[]'::jsonb;


ALTER TABLE review_queue

ADD COLUMN IF NOT EXISTS review_hash CHAR(64);


CREATE UNIQUE INDEX IF NOT EXISTS ux_review_queue_review_hash

ON review_queue(review_hash)

WHERE review_hash IS NOT NULL;


CREATE INDEX IF NOT EXISTS ix_review_queue_reason_codes

ON review_queue USING GIN(reason_codes);



CREATE TABLE IF NOT EXISTS dead_letter_queue (

    dlq_id SERIAL PRIMARY KEY,

    source_type VARCHAR(50),

    record_id UUID,

    raw_payload JSONB,

    error_message TEXT,

    reason_code VARCHAR(100),

    reason_codes JSONB DEFAULT '[]'::jsonb,

    validation_report JSONB,

    dead_letter_hash CHAR(64),

    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE dead_letter_queue

ADD COLUMN IF NOT EXISTS reason_code VARCHAR(100);


ALTER TABLE dead_letter_queue

ADD COLUMN IF NOT EXISTS reason_codes JSONB DEFAULT '[]'::jsonb;


ALTER TABLE dead_letter_queue

ADD COLUMN IF NOT EXISTS dead_letter_hash CHAR(64);


CREATE UNIQUE INDEX IF NOT EXISTS ux_dead_letter_queue_hash

ON dead_letter_queue(dead_letter_hash)

WHERE dead_letter_hash IS NOT NULL;


CREATE INDEX IF NOT EXISTS ix_dead_letter_queue_reason_codes

ON dead_letter_queue USING GIN(reason_codes);
