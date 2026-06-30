CREATE OR REPLACE VIEW recipe_with_instructions AS
SELECT
    r.recipe_id,
    r.title,
    r.description,
    r.cuisine,
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
    r.source_type,
    r.source_url,
    r.language;
