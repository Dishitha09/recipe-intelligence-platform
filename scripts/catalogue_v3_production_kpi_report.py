import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


def catalogue_v3_production_kpi_report():
    with get_catalogue_v3_engine().connect() as conn:
        summary = dict(
            conn.execute(
                text(
                    """
                    SELECT
                        (SELECT count(*) FROM recipe_catalogue_v3) AS recipes,
                        (
                            SELECT count(*)
                            FROM recipe_catalogue_v3
                            WHERE jsonb_array_length(ingredients_json) > 0
                        ) AS recipes_with_ingredients,
                        (
                            SELECT count(*)
                            FROM recipe_catalogue_v3
                            WHERE jsonb_array_length(cook_steps) > 0
                        ) AS recipes_with_steps,
                        (
                            SELECT count(*)
                            FROM recipe_catalogue_v3
                            CROSS JOIN LATERAL jsonb_array_elements(ingredients_json)
                                AS ingredient
                        ) AS ingredient_rows,
                        (SELECT count(*) FROM master_ingredients)
                            AS master_ingredients,
                        (SELECT count(*) FROM ingredient_aliases)
                            AS ingredient_aliases,
                        (
                            SELECT count(*)
                            FROM ingredient_embeddings
                        ) AS ingredient_embeddings,
                        (
                            SELECT count(*)
                            FROM ingredient_resolution_reports
                        ) AS ingredient_resolution_reports
                    """
                )
            ).mappings().one()
        )
        validation = dict(
            conn.execute(
                text(
                    """
                    WITH latest AS (
                        SELECT DISTINCT ON (recipe_id)
                            recipe_id,
                            status,
                            check_results
                        FROM validation_reports
                        ORDER BY recipe_id, validation_id DESC
                    )
                    SELECT
                        count(*) AS validated_recipes,
                        count(*) FILTER (WHERE status = 'ACCEPTED')
                            AS accepted,
                        count(*) FILTER (WHERE status = 'REVIEW')
                            AS review,
                        count(*) FILTER (WHERE status = 'REJECTED')
                            AS rejected,
                        count(*) FILTER (
                            WHERE status = 'ACCEPTED'
                              AND EXISTS (
                                  SELECT 1
                                  FROM jsonb_array_elements(check_results)
                                      AS check_result
                                  WHERE COALESCE(
                                      (check_result->>'passed')::boolean,
                                      true
                                  ) IS FALSE
                                  AND check_result->>'severity' = 'CRITICAL'
                              )
                        ) AS accepted_critical_failures
                    FROM latest
                    """
                )
            ).mappings().one()
        )
        resolution = dict(
            conn.execute(
                text(
                    """
                    WITH latest AS (
                        SELECT DISTINCT ON (recipe_id, source_position)
                            recipe_id,
                            source_position,
                            master_ingredient_id,
                            tier
                        FROM ingredient_resolution_reports
                        ORDER BY recipe_id, source_position, resolution_id DESC
                    )
                    SELECT
                        count(*) AS reported_ingredient_rows,
                        count(*) FILTER (
                            WHERE master_ingredient_id IS NOT NULL
                        ) AS resolved_rows,
                        count(*) FILTER (
                            WHERE master_ingredient_id IS NULL
                        ) AS unresolved_rows,
                        count(*) FILTER (WHERE tier = 'exact_alias')
                            AS exact_alias_rows,
                        count(*) FILTER (WHERE tier = 'vector_similarity')
                            AS vector_rows,
                        count(*) FILTER (WHERE tier = 'llm_escalation')
                            AS llm_rows
                    FROM latest
                    """
                )
            ).mappings().one()
        )

    validation_rate = _rate(
        validation["accepted"],
        validation["validated_recipes"],
    )
    resolution_rate = _rate(
        resolution["resolved_rows"],
        resolution["reported_ingredient_rows"],
    )
    embedding_coverage = _rate(
        summary["ingredient_embeddings"],
        summary["master_ingredients"],
    )

    return {
        "database": "recipe_catalogue_v3",
        "summary": summary,
        "validation": {
            **validation,
            "validation_acceptance_rate": round(validation_rate, 4),
            "passes_ps5_kpi": (
                validation_rate >= 0.85
                and validation["accepted_critical_failures"] == 0
            ),
        },
        "ingredient_resolution": {
            **resolution,
            "ingredient_resolution_rate": round(resolution_rate, 4),
            "passes_ps3_kpi": resolution_rate >= 0.94,
            "llm_escalation_rate": round(
                _rate(
                    resolution["llm_rows"],
                    resolution["reported_ingredient_rows"],
                ),
                4,
            ),
        },
        "embedding_coverage": {
            "ingredient_embedding_coverage": round(embedding_coverage, 4),
            "passes_embedding_coverage": embedding_coverage >= 0.99,
        },
    }


def _rate(numerator, denominator):
    return float(numerator or 0) / float(denominator or 0) if denominator else 0.0


def main():
    print(
        json.dumps(
            catalogue_v3_production_kpi_report(),
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
