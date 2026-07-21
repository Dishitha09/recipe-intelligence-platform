import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_curator_repository import (
    CatalogueV3CuratorRepository,
)
from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
)


DEFAULT_CORRECTIONS = [
    {
        "canonical_name": "coriander_leaves",
        "alias_name": "coriander dhania leaves",
        "language": "en",
    },
    {
        "canonical_name": "radish",
        "alias_name": "mooli mullangi radish",
        "language": "en",
    },
    {
        "canonical_name": "fresh_cream",
        "alias_name": "fresh cream",
        "language": "en",
    },
    {
        "canonical_name": "cumin_powder",
        "alias_name": "cumin powder jeera",
        "language": "en",
    },
    {
        "canonical_name": "black_salt",
        "alias_name": "black salt kala namak",
        "language": "en",
    },
]


def run_catalogue_v3_curator_workflow_proof(
    output_path=Path("evidence/catalogue_v3_curator_workflow_latest.json"),
):
    repository = CatalogueV3CuratorRepository()
    before = _unresolved_count()
    corrections = []

    for correction in DEFAULT_CORRECTIONS:
        result = repository.write_back_alias(
            source="curator_workflow_proof",
            corrected_by="production-proof",
            **correction,
        )
        verification = repository.resolve_alias(correction["alias_name"])
        corrections.append(
            {
                **correction,
                "write_back": result,
                "verification": verification,
                "passes_tier1_next_run": (
                    verification is not None
                    and verification["resolution_tier"] == "exact_alias"
                    and verification["resolution_method"] == "database_alias"
                ),
            }
        )

    updated_rows = _apply_corrections_to_catalogue(corrections)
    after = _unresolved_count()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": "recipe_catalogue_v3",
        "workflow": "review correction -> alias write-back -> catalogue update -> next run Tier 1",
        "before_unresolved_ingredient_mentions": before,
        "after_unresolved_ingredient_mentions": after,
        "catalogue_rows_updated": updated_rows,
        "corrections": corrections,
        "passes_curator_workflow": (
            bool(corrections)
            and all(item["passes_tier1_next_run"] for item in corrections)
            and after <= before
        ),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
    report["output_path"] = str(output_path)
    return report


def _unresolved_count():
    with get_catalogue_v3_engine().connect() as conn:
        return int(
            conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM recipe_catalogue_v3 r
                    CROSS JOIN LATERAL jsonb_array_elements(r.ingredients_json)
                        AS ingredient
                    WHERE ingredient ? 'enrichment_flags'
                      AND ingredient->'enrichment_flags'
                          ? 'unresolved_ingredient'
                    """
                )
            ).scalar()
            or 0
        )


def _apply_corrections_to_catalogue(corrections):
    lookup = {
        normalize_ingredient_name(item["alias_name"]): item
        for item in corrections
    }
    updated_rows = 0

    with get_catalogue_v3_engine().begin() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT recipe_id, ingredients_json
                    FROM recipe_catalogue_v3
                    WHERE is_active IS TRUE
                    """
                )
            ).mappings()
        ]

        for row in rows:
            ingredients = list(row["ingredients_json"] or [])
            changed = False

            for ingredient in ingredients:
                raw_name = (
                    ingredient.get("name")
                    or ingredient.get("item")
                    or ingredient.get("raw_text")
                    or ""
                )
                correction = lookup.get(normalize_ingredient_name(raw_name))

                if not correction:
                    continue

                verification = correction["verification"]
                ingredient["canonical_name"] = verification["canonical_name"]
                ingredient["master_ingredient_id"] = verification["ingredient_id"]
                ingredient["resolution_tier"] = "exact_alias"
                ingredient["resolution_method"] = "database_alias"
                ingredient["resolution_confidence"] = 1.0
                ingredient["enrichment_flags"] = [
                    flag
                    for flag in ingredient.get("enrichment_flags", [])
                    if flag != "unresolved_ingredient"
                ]
                changed = True

            if changed:
                conn.execute(
                    text(
                        """
                        UPDATE recipe_catalogue_v3
                        SET
                            ingredients_json = CAST(:ingredients_json AS jsonb),
                            updated_at = CURRENT_TIMESTAMP
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
                updated_rows += 1

    return updated_rows


def main():
    print(
        json.dumps(
            run_catalogue_v3_curator_workflow_proof(),
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
