import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.fingerprints import stable_hash
from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
    resolve_alias_match,
)


SELECT_RECIPES_SQL = text(
    """
    SELECT recipe_id, ingredients_json
    FROM recipe_catalogue_v3
    WHERE is_active IS TRUE
    ORDER BY created_at, recipe_id
    LIMIT :limit
    """
)


def resolve_catalogue_v3_ingredients(limit=100000, dry_run=False):
    engine = get_catalogue_v3_engine()

    with engine.begin() as conn:
        master_lookup = _master_lookup(conn)
        rows = [
            dict(row)
            for row in conn.execute(
                SELECT_RECIPES_SQL,
                {"limit": limit},
            ).mappings()
        ]
        total = 0
        resolved = 0
        updated_recipes = 0
        tier_counts = Counter()
        method_counts = Counter()
        unresolved_samples = []

        for row in rows:
            ingredients = list(row.get("ingredients_json") or [])
            changed = False

            for index, ingredient in enumerate(ingredients, start=1):
                total += 1
                result = _resolve_ingredient(
                    conn,
                    master_lookup,
                    ingredient,
                )

                tier_counts[result["tier"]] += 1
                method_counts[result["method"]] += 1

                if result["master_ingredient_id"] is not None:
                    resolved += 1
                    for key in [
                        "master_ingredient_id",
                        "canonical_name",
                        "resolution_method",
                        "resolution_tier",
                        "resolution_confidence",
                    ]:
                        if ingredient.get(key) != result.get(key):
                            ingredient[key] = result[key]
                            changed = True
                else:
                    ingredient["enrichment_flags"] = _dedupe(
                        list(ingredient.get("enrichment_flags") or [])
                        + ["unresolved_ingredient"]
                    )
                    changed = True

                    if len(unresolved_samples) < 20:
                        unresolved_samples.append(
                            {
                                "recipe_id": str(row["recipe_id"]),
                                "raw_name": result["raw_name"],
                                "normalized_name": result["normalized_name"],
                            }
                        )

                if not dry_run:
                    _save_resolution_report(
                        conn,
                        row["recipe_id"],
                        index,
                        result,
                    )

            if changed and not dry_run:
                conn.execute(
                    text(
                        """
                        UPDATE recipe_catalogue_v3
                        SET ingredients_json = CAST(:ingredients_json AS jsonb)
                        WHERE recipe_id = :recipe_id
                        """
                    ),
                    {
                        "recipe_id": row["recipe_id"],
                        "ingredients_json": json.dumps(
                            ingredients,
                            default=str,
                        ),
                    },
                )
                updated_recipes += 1

    resolution_rate = resolved / total if total else 0

    return {
        "recipes_selected": len(rows),
        "ingredient_rows": total,
        "resolved_rows": resolved,
        "unresolved_rows": total - resolved,
        "ingredient_resolution_rate": round(resolution_rate, 4),
        "tier_counts": dict(tier_counts),
        "method_counts": dict(method_counts),
        "updated_recipes": updated_recipes,
        "dry_run": dry_run,
        "passes_ps3_kpi": resolution_rate >= 0.94,
        "unresolved_samples": unresolved_samples,
    }


def _master_lookup(conn):
    rows = [
        dict(row)
        for row in conn.execute(
            text(
                """
                SELECT ingredient_id, canonical_name
                FROM master_ingredients
                """
            )
        ).mappings()
    ]
    aliases = [
        dict(row)
        for row in conn.execute(
            text(
                """
                SELECT ia.alias_name, mi.ingredient_id, mi.canonical_name
                FROM ingredient_aliases ia
                JOIN master_ingredients mi
                    ON mi.ingredient_id = ia.ingredient_id
                """
            )
        ).mappings()
    ]
    lookup = {}

    for row in rows:
        _add_lookup_value(
            lookup,
            row["canonical_name"],
            row["ingredient_id"],
            row["canonical_name"],
        )
        _add_lookup_value(
            lookup,
            str(row["canonical_name"]).replace("_", " "),
            row["ingredient_id"],
            row["canonical_name"],
        )

    for row in aliases:
        _add_lookup_value(
            lookup,
            row["alias_name"],
            row["ingredient_id"],
            row["canonical_name"],
        )

    return lookup


def _add_lookup_value(lookup, name, ingredient_id, canonical_name):
    normalized = normalize_ingredient_name(name)

    if normalized:
        lookup[normalized] = {
            "master_ingredient_id": ingredient_id,
            "canonical_name": canonical_name,
        }


def _resolve_ingredient(conn, master_lookup, ingredient):
    raw_name = (
        ingredient.get("name")
        or ingredient.get("item")
        or ingredient.get("raw_text")
        or ""
    )
    normalized_name = normalize_ingredient_name(raw_name)

    if not normalized_name:
        return _unresolved(raw_name, normalized_name)

    exact = master_lookup.get(normalized_name)

    if exact:
        return _resolved(
            raw_name=raw_name,
            normalized_name=normalized_name,
            canonical_name=exact["canonical_name"],
            master_ingredient_id=exact["master_ingredient_id"],
            method="database_alias",
            tier="exact_alias",
            confidence_score=1.0,
        )

    alias_result = resolve_alias_match(raw_name)

    if alias_result and alias_result.get("canonical_name"):
        canonical_name = alias_result["canonical_name"]
        master = _ensure_master_and_alias(
            conn,
            master_lookup,
            canonical_name,
            raw_name,
        )

        return _resolved(
            raw_name=raw_name,
            normalized_name=normalized_name,
            canonical_name=master["canonical_name"],
            master_ingredient_id=master["master_ingredient_id"],
            method="alias_catalogue_writeback",
            tier="exact_alias",
            confidence_score=alias_result.get("confidence_score") or 1.0,
        )

    return _unresolved(raw_name, normalized_name)


def _ensure_master_and_alias(conn, master_lookup, canonical_name, alias_name):
    normalized_canonical = normalize_ingredient_name(canonical_name).replace(
        " ",
        "_",
    )
    existing = master_lookup.get(
        normalize_ingredient_name(normalized_canonical)
    ) or master_lookup.get(
        normalize_ingredient_name(normalized_canonical.replace("_", " "))
    )

    if existing:
        master = existing
    else:
        ingredient_id = conn.execute(
            text(
                """
                INSERT INTO master_ingredients (canonical_name)
                VALUES (:canonical_name)
                ON CONFLICT (canonical_name)
                DO UPDATE SET canonical_name = EXCLUDED.canonical_name
                RETURNING ingredient_id
                """
            ),
            {"canonical_name": normalized_canonical},
        ).scalar()
        master = {
            "master_ingredient_id": ingredient_id,
            "canonical_name": normalized_canonical,
        }
        _add_lookup_value(
            master_lookup,
            normalized_canonical,
            ingredient_id,
            normalized_canonical,
        )

    normalized_alias = normalize_ingredient_name(alias_name)

    if normalized_alias and normalized_alias not in master_lookup:
        conn.execute(
            text(
                """
                INSERT INTO ingredient_aliases (
                    ingredient_id, alias_name, source
                )
                VALUES (:ingredient_id, :alias_name, 'catalogue_v3_resolution')
                ON CONFLICT (LOWER(alias_name)) DO NOTHING
                """
            ),
            {
                "ingredient_id": master["master_ingredient_id"],
                "alias_name": normalized_alias,
            },
        )
        _add_lookup_value(
            master_lookup,
            normalized_alias,
            master["master_ingredient_id"],
            master["canonical_name"],
        )

    return master


def _resolved(
    raw_name,
    normalized_name,
    canonical_name,
    master_ingredient_id,
    method,
    tier,
    confidence_score,
):
    return {
        "raw_name": raw_name,
        "normalized_name": normalized_name,
        "canonical_name": canonical_name,
        "master_ingredient_id": master_ingredient_id,
        "method": method,
        "tier": tier,
        "confidence_score": round(float(confidence_score), 4),
        "enrichment_flags": [],
        "resolution_method": method,
        "resolution_tier": tier,
        "resolution_confidence": round(float(confidence_score), 4),
    }


def _unresolved(raw_name, normalized_name):
    return {
        "raw_name": raw_name,
        "normalized_name": normalized_name,
        "canonical_name": None,
        "master_ingredient_id": None,
        "method": "unresolved",
        "tier": "unresolved",
        "confidence_score": 0.0,
        "enrichment_flags": ["unresolved_ingredient"],
        "resolution_method": "unresolved",
        "resolution_tier": "unresolved",
        "resolution_confidence": 0.0,
    }


def _save_resolution_report(conn, recipe_id, source_position, result):
    payload = {
        "recipe_id": str(recipe_id),
        "source_position": source_position,
        **result,
    }
    report_hash = stable_hash(payload)

    conn.execute(
        text(
            """
            INSERT INTO ingredient_resolution_reports (
                recipe_id, source_position, raw_name, normalized_name,
                canonical_name, master_ingredient_id, method, tier,
                confidence_score, enrichment_flags, report_hash
            )
            VALUES (
                CAST(:recipe_id AS uuid), :source_position, :raw_name,
                :normalized_name, :canonical_name, :master_ingredient_id,
                :method, :tier, :confidence_score,
                CAST(:enrichment_flags AS jsonb), :report_hash
            )
            ON CONFLICT (report_hash) DO NOTHING
            """
        ),
        {
            "recipe_id": str(recipe_id),
            "source_position": source_position,
            "raw_name": result["raw_name"],
            "normalized_name": result["normalized_name"],
            "canonical_name": result["canonical_name"],
            "master_ingredient_id": result["master_ingredient_id"],
            "method": result["method"],
            "tier": result["tier"],
            "confidence_score": result["confidence_score"],
            "enrichment_flags": json.dumps(result["enrichment_flags"]),
            "report_hash": report_hash,
        },
    )


def _dedupe(values):
    deduped = []

    for value in values:
        if value not in deduped:
            deduped.append(value)

    return deduped


def main():
    parser = argparse.ArgumentParser(
        description="Resolve recipe_catalogue_v3 ingredient JSON against v3 master ingredients."
    )
    parser.add_argument("--limit", type=int, default=100000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        json.dumps(
            resolve_catalogue_v3_ingredients(
                limit=args.limit,
                dry_run=args.dry_run,
            ),
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
