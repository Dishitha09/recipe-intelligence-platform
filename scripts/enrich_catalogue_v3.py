import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_loader import CatalogueV3Loader
from services.enrichment.catalogue_v3_enricher import CatalogueV3Enricher


SELECT_SQL = text(
    """
    SELECT
        recipe_id,
        name,
        description,
        nutrition_info,
        tags,
        metadata,
        servings,
        difficulty_level,
        image_url,
        course,
        region,
        diet,
        budget_band,
        diet_tags,
        allergen_tags,
        cuisines,
        meal_types,
        dish_types,
        prep_time_min,
        cook_time_min,
        total_time_min,
        ingredients_json,
        cook_steps,
        quick_steps,
        meal_role,
        dish_family,
        health_tags,
        efficiency_tags,
        cost_tier,
        source
    FROM recipe_catalogue_v3
    WHERE (:source IS NULL OR source = :source)
    ORDER BY created_at, recipe_id
    LIMIT :limit
    """
)

UPDATE_SQL = text(
    """
    UPDATE recipe_catalogue_v3
    SET
        ingredients_json = CAST(:ingredients_json AS jsonb),
        metadata = metadata || CAST(:metadata_patch AS jsonb),
        difficulty_level = COALESCE(difficulty_level, :difficulty_level),
        diet = COALESCE(diet, :diet),
        budget_band = COALESCE(budget_band, :budget_band),
        region = COALESCE(region, :region),
        diet_tags = CAST(:diet_tags AS text[]),
        allergen_tags = CAST(:allergen_tags AS text[]),
        dish_types = CAST(:dish_types AS text[]),
        meal_role = COALESCE(meal_role, :meal_role),
        dish_family = COALESCE(dish_family, :dish_family),
        health_tags = CAST(:health_tags AS text[]),
        efficiency_tags = CAST(:efficiency_tags AS text[]),
        cost_tier = COALESCE(cost_tier, :cost_tier),
        complexity = COALESCE(complexity, :complexity)
    WHERE recipe_id = :recipe_id
    """
)


def enrich_catalogue_v3(source=None, limit=100000, dry_run=False):
    engine = get_catalogue_v3_engine()
    enricher = CatalogueV3Enricher()
    loader = CatalogueV3Loader(engine=engine)
    updated = 0
    samples = []

    with engine.begin() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                SELECT_SQL,
                {"source": source, "limit": limit},
            ).mappings()
        ]

        for row in rows:
            result = enricher.enrich_row(row)
            params = _params(row, result.updates, result.metadata_patch, loader)

            if not dry_run:
                conn.execute(UPDATE_SQL, params)

            updated += 1

            if len(samples) < 5:
                samples.append(
                    {
                        "name": row["name"],
                        "source": row["source"],
                        "updates": {
                            key: value
                            for key, value in result.updates.items()
                            if key != "ingredients_json"
                        },
                    }
                )

    return {
        "source": source,
        "selected": len(rows),
        "updated": updated if not dry_run else 0,
        "dry_run": dry_run,
        "samples": samples,
    }


def _params(row, updates, metadata_patch, loader):
    merged = {
        "ingredients_json": updates.get(
            "ingredients_json",
            row.get("ingredients_json") or [],
        ),
        "metadata": metadata_patch,
        "difficulty_level": updates.get("difficulty_level"),
        "diet": updates.get("diet"),
        "budget_band": updates.get("budget_band"),
        "region": updates.get("region"),
        "diet_tags": updates.get("diet_tags", row.get("diet_tags") or []),
        "allergen_tags": updates.get(
            "allergen_tags",
            row.get("allergen_tags") or [],
        ),
        "dish_types": updates.get("dish_types", row.get("dish_types") or []),
        "meal_role": updates.get("meal_role"),
        "dish_family": updates.get("dish_family"),
        "health_tags": updates.get("health_tags", row.get("health_tags") or []),
        "efficiency_tags": updates.get(
            "efficiency_tags",
            row.get("efficiency_tags") or [],
        ),
        "cost_tier": updates.get("cost_tier"),
        "complexity": updates.get("complexity"),
    }
    normalized = loader._normalize_payload(
        {
            "name": row["name"],
            "servings": row["servings"],
            **merged,
        }
    )

    return {
        "recipe_id": row["recipe_id"],
        "ingredients_json": normalized["ingredients_json"],
        "metadata_patch": json.dumps(metadata_patch),
        "difficulty_level": normalized["difficulty_level"],
        "diet": normalized["diet"],
        "budget_band": normalized["budget_band"],
        "region": normalized["region"],
        "diet_tags": normalized["diet_tags"],
        "allergen_tags": normalized["allergen_tags"],
        "dish_types": normalized["dish_types"],
        "meal_role": normalized["meal_role"],
        "dish_family": normalized["dish_family"],
        "health_tags": normalized["health_tags"],
        "efficiency_tags": normalized["efficiency_tags"],
        "cost_tier": normalized["cost_tier"],
        "complexity": normalized["complexity"],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Enrich recipe_catalogue_v3 rows with deterministic fields."
    )
    parser.add_argument("--source", default=None)
    parser.add_argument("--limit", type=int, default=100000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        json.dumps(
            enrich_catalogue_v3(
                source=args.source,
                limit=args.limit,
                dry_run=args.dry_run,
            ),
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
