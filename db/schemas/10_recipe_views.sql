DROP VIEW IF EXISTS recipe_with_instructions;
DROP VIEW IF EXISTS recipe_state_target_coverage;
DROP VIEW IF EXISTS indian_state_reference;
DROP VIEW IF EXISTS recipe_instruction_summary;
DROP VIEW IF EXISTS recipe_instruction_details;
DROP VIEW IF EXISTS recipe_instructions;


CREATE OR REPLACE VIEW recipe_with_instructions AS
SELECT
    r.recipe_id,
    r.title,
    r.description,
    r.cuisine,
    COALESCE(r.state, 'Unclassified') AS state,
    COALESCE(r.region, 'Unclassified') AS region,
    r.state_confidence,
    r.state_method,
    r.source_type,
    r.source_url,
    r.language,
    r.created_at,
    r.updated_at,
    COUNT(rs.recipe_id) AS step_count,
    STRING_AGG(
        rs.step_number::text || '. ' || rs.instruction,
        E'\n'
        ORDER BY rs.step_number
    ) AS instructions,
    REGEXP_REPLACE(
        STRING_AGG(
            rs.step_number::text || '. ' || rs.instruction,
            ' '
            ORDER BY rs.step_number
        ),
        '\s+',
        ' ',
        'g'
    ) AS instructions_one_line
FROM recipes r
LEFT JOIN recipe_steps rs
    ON rs.recipe_id = r.recipe_id
GROUP BY
    r.recipe_id,
    r.title,
    r.description,
    r.cuisine,
    COALESCE(r.state, 'Unclassified'),
    COALESCE(r.region, 'Unclassified'),
    r.state_confidence,
    r.state_method,
    r.source_type,
    r.source_url,
    r.language,
    r.created_at,
    r.updated_at;


CREATE OR REPLACE VIEW recipe_instructions AS
SELECT
    recipe_step_id AS instruction_id,
    recipe_id,
    step_number,
    instruction
FROM recipe_steps;


CREATE OR REPLACE VIEW recipe_instruction_details AS
SELECT
    rs.recipe_step_id AS instruction_id,
    r.recipe_id,
    r.title,
    COALESCE(r.state, 'Unclassified') AS state,
    COALESCE(r.region, 'Unclassified') AS region,
    r.source_type,
    r.source_url,
    rs.step_number,
    rs.instruction
FROM recipe_steps rs
JOIN recipes r
    ON r.recipe_id = rs.recipe_id;


CREATE OR REPLACE VIEW recipe_instruction_summary AS
SELECT
    r.recipe_id,
    r.title,
    COALESCE(r.state, 'Unclassified') AS state,
    COALESCE(r.region, 'Unclassified') AS region,
    r.source_type,
    r.source_url,
    COUNT(rs.recipe_step_id) AS step_count,
    REGEXP_REPLACE(
        STRING_AGG(
            rs.step_number::text || '. ' || rs.instruction,
            ' '
            ORDER BY rs.step_number
        ),
        '\s+',
        ' ',
        'g'
    ) AS instructions
FROM recipes r
LEFT JOIN recipe_steps rs
    ON rs.recipe_id = r.recipe_id
GROUP BY
    r.recipe_id,
    r.title,
    r.state,
    r.region,
    r.source_type,
    r.source_url;


DROP VIEW IF EXISTS recipe_state_coverage;


CREATE OR REPLACE VIEW recipe_state_coverage AS
SELECT
    COALESCE(state, 'Unclassified') AS state,
    COALESCE(region, 'Unclassified') AS region,
    COUNT(*) AS recipe_count,
    ROUND(AVG(COALESCE(state_confidence, 0))::numeric, 4) AS avg_state_confidence,
    COUNT(*) FILTER (
        WHERE source_url LIKE 'https://www.indianhealthyrecipes.com/%'
    ) AS indianhealthyrecipes_count,
    COUNT(DISTINCT source_url) FILTER (
        WHERE source_url IS NOT NULL
    ) AS distinct_source_urls
FROM recipes
GROUP BY
    COALESCE(state, 'Unclassified'),
    COALESCE(region, 'Unclassified');


CREATE OR REPLACE VIEW indian_state_reference AS
SELECT *
FROM (
    VALUES
        ('Andhra Pradesh', 'South', 'state'),
        ('Arunachal Pradesh', 'Northeast', 'state'),
        ('Assam', 'Northeast', 'state'),
        ('Bihar', 'East', 'state'),
        ('Chhattisgarh', 'Central', 'state'),
        ('Goa', 'West', 'state'),
        ('Gujarat', 'West', 'state'),
        ('Haryana', 'North', 'state'),
        ('Himachal Pradesh', 'North', 'state'),
        ('Jharkhand', 'East', 'state'),
        ('Karnataka', 'South', 'state'),
        ('Kerala', 'South', 'state'),
        ('Madhya Pradesh', 'Central', 'state'),
        ('Maharashtra', 'West', 'state'),
        ('Manipur', 'Northeast', 'state'),
        ('Meghalaya', 'Northeast', 'state'),
        ('Mizoram', 'Northeast', 'state'),
        ('Nagaland', 'Northeast', 'state'),
        ('Odisha', 'East', 'state'),
        ('Punjab', 'North', 'state'),
        ('Rajasthan', 'Northwest', 'state'),
        ('Sikkim', 'Northeast', 'state'),
        ('Tamil Nadu', 'South', 'state'),
        ('Telangana', 'South', 'state'),
        ('Tripura', 'Northeast', 'state'),
        ('Uttar Pradesh', 'North', 'state'),
        ('Uttarakhand', 'North', 'state'),
        ('West Bengal', 'East', 'state'),
        ('Delhi', 'North', 'union_territory'),
        ('Puducherry', 'South', 'union_territory'),
        ('Chandigarh', 'North', 'union_territory'),
        ('Lakshadweep', 'Southwest', 'union_territory'),
        ('Andaman and Nicobar', 'Island', 'union_territory'),
        ('Dadra and Nagar Haveli and Daman and Diu', 'West', 'union_territory'),
        ('Ladakh', 'North', 'union_territory'),
        ('Jammu and Kashmir', 'North', 'union_territory')
) AS states(state, region, place_type);


CREATE OR REPLACE VIEW recipe_state_target_coverage AS
SELECT
    ref.state,
    ref.region,
    ref.place_type,
    COALESCE(c.recipe_count, 0) AS recipe_count,
    COALESCE(c.avg_state_confidence, 0) AS avg_state_confidence,
    COALESCE(c.distinct_source_urls, 0) AS distinct_source_urls,
    278 AS target_for_10000,
    GREATEST(278 - COALESCE(c.recipe_count, 0), 0) AS remaining_for_10000
FROM indian_state_reference ref
LEFT JOIN recipe_state_coverage c
    ON c.state = ref.state
ORDER BY
    remaining_for_10000 DESC,
    ref.state ASC;
