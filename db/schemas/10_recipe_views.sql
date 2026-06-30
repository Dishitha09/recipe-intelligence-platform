DROP VIEW IF EXISTS recipe_with_instructions;


CREATE OR REPLACE VIEW recipe_with_instructions AS
SELECT
    r.recipe_id,
    r.title,
    r.description,
    r.cuisine,
    r.state,
    r.region,
    r.state_confidence,
    r.state_method,
    r.source_type,
    r.source_url,
    r.language,
    COUNT(rs.recipe_id) AS step_count,
    STRING_AGG(
        rs.step_number::text || '. ' || rs.instruction,
        E'\n'
        ORDER BY rs.step_number
    ) AS instructions
FROM recipes r
LEFT JOIN recipe_steps rs
    ON rs.recipe_id = r.recipe_id
GROUP BY
    r.recipe_id,
    r.title,
    r.description,
    r.cuisine,
    r.state,
    r.region,
    r.state_confidence,
    r.state_method,
    r.source_type,
    r.source_url,
    r.language;


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
