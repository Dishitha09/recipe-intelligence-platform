import argparse
import json
import re

from sqlalchemy import bindparam, text

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


def bulk_normalized_fallback(limit=None, dry_run=False, chunk_size=1000):
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
    canonical_names = set()

    for row in rows:
        resolved = _normalized_fallback(row.ingredient_name)
        canonical_name = resolved.get("canonical_name")

        if not canonical_name:
            continue

        canonical_names.add(canonical_name)
        updates.append(
            {
                "recipe_ingredient_id": row.recipe_ingredient_id,
                "canonical_name": canonical_name,
                "resolution_method": resolved.get("method"),
                "resolution_tier": resolved.get("tier"),
                "resolution_confidence": resolved.get("confidence_score"),
                "enrichment_flags": json.dumps(
                    resolved.get("enrichment_flags", [])
                ),
            }
        )

    if dry_run or not updates:
        return {
            "examined": len(rows),
            "updated": len(updates),
            "unique_canonical_names": len(canonical_names),
            "dry_run": dry_run,
            "bulk": True,
        }

    canonical_names = sorted(canonical_names)

    with engine.begin() as conn:
        for chunk in _chunks(canonical_names, chunk_size):
            conn.execute(
                text(
                    """
                    INSERT INTO master_ingredients (canonical_name)
                    VALUES (:canonical_name)
                    ON CONFLICT (canonical_name) DO NOTHING
                    """
                ),
                [{"canonical_name": name} for name in chunk],
            )

        id_lookup = {}
        select_stmt = text(
            """
            SELECT ingredient_id, canonical_name
            FROM master_ingredients
            WHERE canonical_name IN :canonical_names
            """
        ).bindparams(bindparam("canonical_names", expanding=True))

        for chunk in _chunks(canonical_names, chunk_size):
            for row in conn.execute(
                select_stmt,
                {"canonical_names": chunk},
            ).mappings():
                id_lookup[row["canonical_name"]] = row["ingredient_id"]

        update_stmt = text(
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
        )

        for chunk in _chunks(updates, chunk_size):
            conn.execute(
                update_stmt,
                [
                    {
                        **update,
                        "ingredient_id": id_lookup[update["canonical_name"]],
                    }
                    for update in chunk
                ],
            )

    return {
        "examined": len(rows),
        "updated": len(updates),
        "unique_canonical_names": len(canonical_names),
        "dry_run": dry_run,
        "bulk": True,
    }


def _chunks(items, chunk_size):
    for index in range(0, len(items), chunk_size):
        yield items[index:index + chunk_size]


def _normalized_fallback(ingredient_name):
    normalized = normalize_ingredient_name(ingredient_name)
    normalized = re.sub(r"\b(?:as needed|optional)\b", " ", normalized)
    normalized = re.sub(r"\([^)]*\)", " ", normalized)
    normalized = re.sub(r"\s+-\s+\d.*$", " ", normalized)
    normalized = re.sub(r"^\s*or\s+\d+\s+", " ", normalized)
    normalized = re.sub(r"^\s*\d+\s+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if not normalized:
        return {"canonical_name": None}

    tokens = normalized.split()

    if len(tokens) > 6:
        return {"canonical_name": None}

    if len(tokens) == 1 and tokens[0] in _MEASUREMENT_WORDS:
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
    parser.add_argument("--bulk-normalized-fallback", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=1000)
    args = parser.parse_args()

    if args.bulk_normalized_fallback:
        print(
            bulk_normalized_fallback(
                limit=args.limit,
                dry_run=args.dry_run,
                chunk_size=args.chunk_size,
            )
        )
    else:
        print(
            backfill(
                limit=args.limit,
                dry_run=args.dry_run,
                use_normalized_fallback=args.use_normalized_fallback,
            )
        )


if __name__ == "__main__":
    main()
