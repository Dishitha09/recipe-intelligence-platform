import argparse
import json
import re

from sqlalchemy import text

from services.database.connection import engine
from services.database.ingredient_repository import IngredientRepository
from services.enrichment.ingredient_resolution.ingredient_resolver import (
    IngredientResolver,
)
from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
)


_MEASUREMENT_WORDS = {
    "cup",
    "cups",
    "gram",
    "grams",
    "kg",
    "tablespoon",
    "tablespoons",
    "tbsp",
    "teaspoon",
    "teaspoons",
    "tsp",
}


def backfill(limit=None, dry_run=False, use_normalized_fallback=False):
    repository = IngredientRepository()
    resolver = IngredientResolver(
        enable_embedding=False,
        ingredient_repository=repository,
    )

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT recipe_ingredient_id, ingredient_name
                FROM recipe_ingredients
                WHERE ingredient_name IS NOT NULL
                  AND trim(ingredient_name) <> ''
                  AND ingredient_id IS NULL
                  AND canonical_name IS NULL
                ORDER BY recipe_ingredient_id
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).fetchall()

    updates = []
    for row in rows:
        resolved = resolver.resolve(row.ingredient_name)
        canonical_name = resolved.get("canonical_name")

        if not canonical_name and use_normalized_fallback:
            resolved = _normalized_fallback(row.ingredient_name)
            canonical_name = resolved.get("canonical_name")

        if not canonical_name:
            continue

        ingredient_id = resolved.get("master_ingredient_id")
        if ingredient_id is None:
            ingredient_id = repository.upsert_master_ingredient(canonical_name)

        updates.append(
            {
                "recipe_ingredient_id": row.recipe_ingredient_id,
                "ingredient_id": ingredient_id,
                "canonical_name": canonical_name,
                "resolution_method": resolved.get("method"),
                "resolution_tier": resolved.get("tier"),
                "resolution_confidence": resolved.get("confidence_score"),
                "enrichment_flags": json.dumps(
                    resolved.get("enrichment_flags", [])
                ),
            }
        )

    if not dry_run and updates:
        with engine.begin() as conn:
            for update in updates:
                conn.execute(
                    text(
                        """
                        UPDATE recipe_ingredients
                        SET
                            ingredient_id = :ingredient_id,
                            canonical_name = :canonical_name,
                            resolution_method = :resolution_method,
                            resolution_tier = :resolution_tier,
                            resolution_confidence = :resolution_confidence,
                            enrichment_flags = CAST(:enrichment_flags AS jsonb)
                        WHERE recipe_ingredient_id = :recipe_ingredient_id
                        """
                    ),
                    update,
                )

    return {
        "examined": len(rows),
        "updated": len(updates),
        "dry_run": dry_run,
        "use_normalized_fallback": use_normalized_fallback,
    }


def _normalized_fallback(ingredient_name):
    normalized = normalize_ingredient_name(ingredient_name)
    normalized = re.sub(r"\b(?:as needed|optional)\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if not normalized:
        return {"canonical_name": None}

    tokens = normalized.split()

    if len(tokens) > 6:
        return {"canonical_name": None}

    if any(token in _MEASUREMENT_WORDS for token in tokens):
        return {"canonical_name": None}

    if any(token.replace(".", "", 1).isdigit() for token in tokens):
        return {"canonical_name": None}

    return {
        "canonical_name": normalized.replace(" ", "_"),
        "method": "normalized_fallback",
        "tier": "curator_review_fallback",
        "confidence_score": 0.55,
        "enrichment_flags": [
            "normalized_fallback",
            "curator_review_required",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Resolve currently unresolved ingredient rows from raw names."
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--use-normalized-fallback", action="store_true")
    args = parser.parse_args()

    print(
        backfill(
            limit=args.limit,
            dry_run=args.dry_run,
            use_normalized_fallback=args.use_normalized_fallback,
        )
    )


if __name__ == "__main__":
    main()
