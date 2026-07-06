import argparse
import json

from sqlalchemy import text

from services.database.connection import engine
from services.ingestion.source_registry import ADAPTER_CLASSES, SourceRegistry


CANONICAL_UNITS = ("g", "ml", "tsp", "tbsp", "cup", "count")


def build_report(config_path="configs/production_recipe_sources.json"):
    with engine.connect() as conn:
        metrics = {
            "recipe_count": _scalar(conn, "SELECT count(*) FROM recipes"),
            "distinct_source_urls": _scalar(
                conn,
                """
                SELECT count(DISTINCT source_url)
                FROM recipes
                WHERE source_url IS NOT NULL
                """,
            ),
            "missing_titles": _scalar(
                conn,
                """
                SELECT count(*)
                FROM recipes
                WHERE title IS NULL OR trim(title) = ''
                """,
            ),
            "recipes_missing_ingredients": _scalar(
                conn,
                """
                SELECT count(*)
                FROM recipes r
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM recipe_ingredients ri
                    WHERE ri.recipe_id = r.recipe_id
                )
                """,
            ),
            "recipes_missing_steps": _scalar(
                conn,
                """
                SELECT count(*)
                FROM recipes r
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM recipe_steps rs
                    WHERE rs.recipe_id = r.recipe_id
                )
                """,
            ),
            "ingredient_rows": _scalar(
                conn,
                "SELECT count(*) FROM recipe_ingredients",
            ),
            "resolved_ingredient_rows": _scalar(
                conn,
                """
                SELECT count(*)
                FROM recipe_ingredients
                WHERE ingredient_id IS NOT NULL
                   OR canonical_name IS NOT NULL
                """,
            ),
            "llm_resolved_rows": _scalar(
                conn,
                """
                SELECT count(*)
                FROM recipe_ingredients
                WHERE resolution_method = 'llm'
                """,
            ),
            "invalid_canonical_unit_rows": _scalar(
                conn,
                """
                SELECT count(*)
                FROM recipe_ingredients
                WHERE canonical_unit IS NOT NULL
                  AND canonical_unit NOT IN ('g', 'ml', 'tsp', 'tbsp', 'cup', 'count')
                """,
            ),
            "density_rows": _scalar(
                conn,
                """
                SELECT count(*)
                FROM master_ingredients
                WHERE density_g_per_ml IS NOT NULL
                """,
            ),
            "validation_reports": _scalar(
                conn,
                "SELECT count(*) FROM validation_reports",
            ),
            "accepted_validation_reports": _scalar(
                conn,
                """
                SELECT count(*)
                FROM validation_reports
                WHERE status = 'ACCEPTED'
                """,
            ),
            "critical_catalogue_failures": _scalar(
                conn,
                """
                SELECT count(*)
                FROM validation_reports
                WHERE recipe_id IS NOT NULL
                  AND failure_codes ?| ARRAY['V01', 'V02', 'V03', 'V09']
                """,
            ),
            "hnsw_indexes": _scalar(
                conn,
                """
                SELECT count(*)
                FROM pg_indexes
                WHERE indexname IN (
                    'idx_ingredient_embeddings_hnsw',
                    'idx_recipe_embeddings_hnsw'
                )
                """,
            ),
        }

    source_registry = SourceRegistry(config_path=config_path)
    adapter_types = set(ADAPTER_CLASSES)
    configured_source_types = {
        source.source_type
        for source in source_registry.configs
    }

    ingredient_resolution_rate = _rate(
        metrics["resolved_ingredient_rows"],
        metrics["ingredient_rows"],
    )
    llm_escalation_rate = _rate(
        metrics["llm_resolved_rows"],
        metrics["ingredient_rows"],
    )
    validation_acceptance_rate = _rate(
        metrics["accepted_validation_reports"],
        metrics["validation_reports"],
    )

    return {
        "summary": {
            **metrics,
            "ingredient_resolution_rate": ingredient_resolution_rate,
            "llm_escalation_rate": llm_escalation_rate,
            "validation_acceptance_rate": validation_acceptance_rate,
            "registered_adapter_types": sorted(adapter_types),
            "configured_source_types": sorted(configured_source_types),
        },
        "acceptance": {
            "PS-1": {
                "description": "7/7 source adapter types operational and registered",
                "passed": len(adapter_types) >= 7,
                "evidence": {
                    "registered_adapter_type_count": len(adapter_types),
                    "registered_adapter_types": sorted(adapter_types),
                },
            },
            "PS-2": {
                "description": "No missing required recipe fields after coercion/load",
                "passed": (
                    metrics["missing_titles"] == 0
                    and metrics["recipes_missing_ingredients"] == 0
                    and metrics["recipes_missing_steps"] == 0
                ),
                "evidence": {
                    "missing_titles": metrics["missing_titles"],
                    "recipes_missing_ingredients": metrics[
                        "recipes_missing_ingredients"
                    ],
                    "recipes_missing_steps": metrics["recipes_missing_steps"],
                },
            },
            "PS-3": {
                "description": "Ingredient resolution target >= 94%; LLM escalation < 10%",
                "passed": (
                    ingredient_resolution_rate >= 0.94
                    and llm_escalation_rate < 0.10
                    and metrics["hnsw_indexes"] >= 2
                ),
                "evidence": {
                    "ingredient_resolution_rate": ingredient_resolution_rate,
                    "llm_escalation_rate": llm_escalation_rate,
                    "hnsw_indexes": metrics["hnsw_indexes"],
                },
            },
            "PS-4": {
                "description": "Canonical unit rows stay inside accepted unit set",
                "passed": metrics["invalid_canonical_unit_rows"] == 0,
                "evidence": {
                    "invalid_canonical_unit_rows": metrics[
                        "invalid_canonical_unit_rows"
                    ],
                    "canonical_units": CANONICAL_UNITS,
                    "density_rows": metrics["density_rows"],
                },
            },
            "PS-5": {
                "description": "Validation acceptance >= 85%; no critical catalogue failures",
                "passed": (
                    validation_acceptance_rate >= 0.85
                    and metrics["critical_catalogue_failures"] == 0
                ),
                "evidence": {
                    "validation_acceptance_rate": validation_acceptance_rate,
                    "critical_catalogue_failures": metrics[
                        "critical_catalogue_failures"
                    ],
                    "validation_reports": metrics["validation_reports"],
                },
            },
        },
    }


def _scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar() or 0


def _rate(numerator, denominator):
    if not denominator:
        return 0.0

    return round(float(numerator) / float(denominator), 4)


def main():
    parser = argparse.ArgumentParser(
        description="Print PS-1 to PS-5 acceptance evidence from PostgreSQL."
    )
    parser.add_argument(
        "--config",
        default="configs/production_recipe_sources.json",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(config_path=args.config)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return

    print("ShopConnect PS-1 to PS-5 acceptance report")
    print("=" * 45)
    for ps_id, item in report["acceptance"].items():
        status = "PASS" if item["passed"] else "FAIL"
        print(f"{ps_id}: {status} - {item['description']}")
        for key, value in item["evidence"].items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
