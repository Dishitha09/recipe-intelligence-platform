import argparse
import json
import sys
import uuid
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_validation_repository import (
    CatalogueV3ValidationRepository,
)
from services.preprocessing.schema_models import Ingredient, Recipe, RecipeStep
from services.validation.validation_engine import ValidationEngine


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
        youtube_url,
        image_url,
        course,
        region,
        diet,
        spice_level,
        complexity,
        budget_band,
        diet_tags,
        allergen_tags,
        cuisines,
        meal_types,
        dish_types,
        texture,
        prep_time_min,
        cook_time_min,
        total_time_min,
        passive_time_min,
        ingredients_json,
        prep_steps,
        cook_steps,
        quick_steps,
        estimated_cost_per_serving,
        popularity_score,
        side_category,
        meal_role,
        dish_family,
        health_tags,
        efficiency_tags,
        experience_tags,
        cost_tier,
        festival_tags,
        owner_code,
        owner_name,
        source,
        language,
        is_public,
        created_by,
        is_active
    FROM recipe_catalogue_v3
    WHERE is_active IS TRUE
    ORDER BY created_at, recipe_id
    LIMIT :limit
    """
)


ALLERGEN_TERMS = {
    "DAIRY": {
        "butter",
        "cheese",
        "cream",
        "curd",
        "ghee",
        "milk",
        "paneer",
        "yogurt",
    },
    "EGG": {"egg", "eggs"},
    "GLUTEN": {
        "atta",
        "bread",
        "flour",
        "maida",
        "pasta",
        "rava",
        "semolina",
        "wheat",
    },
    "NUTS": {
        "almond",
        "almonds",
        "cashew",
        "cashews",
        "peanut",
        "peanuts",
        "pistachio",
        "walnut",
    },
    "SEAFOOD": {"fish", "prawn", "prawns", "shrimp"},
    "SOY": {"soy", "soya", "tofu"},
}


def validate_catalogue_v3(limit=100000, dry_run=False):
    engine = get_catalogue_v3_engine()
    repository = CatalogueV3ValidationRepository(engine=engine)
    validation_engine = ValidationEngine()
    status_counts = Counter()
    failure_counts = Counter()
    persisted = Counter()
    samples = []

    with engine.connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(SELECT_SQL, {"limit": limit}).mappings()
        ]

    for row in rows:
        recipe = row_to_recipe(row)
        report = validation_engine.validate(recipe)
        status_counts[report.status] += 1

        for result in report.check_results:
            if not result.passed:
                failure_counts[result.check_id] += 1

        if not dry_run:
            repository.save_report(
                recipe_id=row["recipe_id"],
                report=report,
            )

            if report.status == "REVIEW":
                repository.save_review(
                    recipe_id=row["recipe_id"],
                    record_id=row["recipe_id"],
                    recipe=recipe,
                    report=report,
                )
                persisted["review_queue"] += 1
            elif report.status == "REJECTED":
                repository.save_dead_letter(
                    recipe_id=row["recipe_id"],
                    record_id=row["recipe_id"],
                    source_type=row.get("source"),
                    raw_payload=row,
                    error_message="Catalogue v3 validation rejected recipe",
                    validation_report=report.model_dump(mode="json"),
                )
                persisted["dead_letter_queue"] += 1

            persisted["validation_reports"] += 1

        if report.status != "ACCEPTED" and len(samples) < 10:
            samples.append(
                {
                    "recipe_id": str(row["recipe_id"]),
                    "name": row["name"],
                    "status": report.status,
                    "failures": [
                        result.check_id
                        for result in report.check_results
                        if not result.passed
                    ],
                }
            )

    total = len(rows)
    accepted = status_counts["ACCEPTED"]
    acceptance_rate = accepted / total if total else 0
    accepted_critical_failures = _accepted_critical_failures(
        engine,
        dry_run=dry_run,
    )

    return {
        "selected": total,
        "dry_run": dry_run,
        "status_counts": dict(status_counts),
        "failure_counts": dict(failure_counts),
        "validation_acceptance_rate": round(acceptance_rate, 4),
        "accepted_critical_failures": accepted_critical_failures,
        "persisted": dict(persisted),
        "samples": samples,
        "passes_ps5_kpi": (
            acceptance_rate >= 0.85
            and accepted_critical_failures == 0
        ),
    }


def row_to_recipe(row):
    ingredients = [
        ingredient_to_model(ingredient)
        for ingredient in row.get("ingredients_json") or []
    ]
    steps = [
        RecipeStep(
            step_number=index,
            instruction=step_text,
        )
        for index, step_text in enumerate(_step_texts(row), start=1)
    ]
    metadata = dict(row.get("metadata") or {})
    metadata.setdefault("nutrition", _nutrition_for_validation(row))
    metadata.setdefault("allergens", list(row.get("allergen_tags") or []))
    metadata.setdefault("dietary_claims", list(row.get("diet_tags") or []))

    source_url = (
        metadata.get("source_url")
        or metadata.get("canonical_url")
        or metadata.get("url")
    )

    return Recipe(
        title=row["name"],
        description=row.get("description"),
        nutrition_info=row.get("nutrition_info") or {},
        tags=list(row.get("tags") or []),
        servings=row.get("servings"),
        difficulty_level=row.get("difficulty_level"),
        youtube_url=row.get("youtube_url"),
        image_url=row.get("image_url"),
        course=list(row.get("course") or []),
        region=row.get("region"),
        language=row.get("language") or "en",
        diet=row.get("diet"),
        spice_level=row.get("spice_level"),
        complexity=row.get("complexity"),
        budget_band=row.get("budget_band"),
        diet_tags=list(row.get("diet_tags") or []),
        allergen_tags=list(row.get("allergen_tags") or []),
        cuisines=list(row.get("cuisines") or []),
        meal_types=list(row.get("meal_types") or []),
        dish_types=list(row.get("dish_types") or []),
        texture=list(row.get("texture") or []),
        prep_time_min=row.get("prep_time_min"),
        cook_time_min=row.get("cook_time_min"),
        total_time_min=row.get("total_time_min"),
        passive_time_min=row.get("passive_time_min"),
        estimated_cost_per_serving=row.get("estimated_cost_per_serving"),
        popularity_score=row.get("popularity_score"),
        side_category=row.get("side_category"),
        meal_role=row.get("meal_role"),
        dish_family=row.get("dish_family"),
        health_tags=list(row.get("health_tags") or []),
        efficiency_tags=list(row.get("efficiency_tags") or []),
        experience_tags=list(row.get("experience_tags") or []),
        cost_tier=row.get("cost_tier"),
        festival_tags=list(row.get("festival_tags") or []),
        ingredients=ingredients,
        steps=steps,
        source_type=row.get("source") or "catalogue_v3",
        source_url=source_url,
        source=row.get("source"),
        owner_code=row.get("owner_code"),
        owner_name=row.get("owner_name"),
        created_by=row.get("created_by"),
        is_public=bool(row.get("is_public")),
        is_active=bool(row.get("is_active")),
        metadata=metadata,
    )


def ingredient_to_model(ingredient):
    name = (
        ingredient.get("name")
        or ingredient.get("item")
        or ingredient.get("raw_text")
        or "unknown"
    )
    flags = list(
        ingredient.get("enrichment_flags")
        or ingredient.get("normalization_flags")
        or []
    )

    return Ingredient(
        ingredient_name=name,
        quantity=_float_or_none(ingredient.get("quantity")),
        unit=ingredient.get("unit"),
        preparation=ingredient.get("prep") or ingredient.get("preparation"),
        canonical_name=ingredient.get("canonical_name") or name,
        master_ingredient_id=ingredient.get("master_ingredient_id"),
        resolution_method=ingredient.get("resolution_method"),
        resolution_tier=ingredient.get("resolution_tier"),
        resolution_confidence=_float_or_none(
            ingredient.get("resolution_confidence")
        ),
        canonical_quantity=_float_or_none(
            ingredient.get("canonical_quantity")
        ),
        canonical_unit=ingredient.get("canonical_unit"),
        conversion_method=ingredient.get("conversion_method"),
        conversion_factor=_float_or_none(ingredient.get("conversion_factor")),
        uom_confidence_score=_float_or_none(
            ingredient.get("uom_confidence_score")
        ),
        enrichment_flags=flags,
        allergen_flags=ingredient.get("allergen_flags")
        or ingredient_allergens(name),
    )


def ingredient_allergens(name):
    normalized = str(name or "").lower()
    return [
        tag
        for tag, terms in ALLERGEN_TERMS.items()
        if any(term in normalized for term in terms)
    ]


def _step_texts(row):
    steps = []

    for step in row.get("cook_steps") or []:
        if isinstance(step, dict):
            text_value = step.get("instruction") or step.get("text")
        else:
            text_value = step

        if text_value:
            steps.append(str(text_value).strip())

    if not steps:
        steps.extend(
            str(step).strip()
            for step in row.get("quick_steps") or []
            if str(step).strip()
        )

    return steps


def _nutrition_for_validation(row):
    nutrition = dict(row.get("nutrition_info") or {})
    kcal = (
        nutrition.get("kcal_per_serving")
        or nutrition.get("calories")
        or nutrition.get("calories_kcal")
    )

    if kcal is None:
        return {}

    return {"kcal_per_serving": _float_or_none(kcal)}


def _float_or_none(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _accepted_critical_failures(engine, dry_run=False):
    if dry_run:
        return 0

    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT count(*)
                FROM validation_reports
                CROSS JOIN LATERAL jsonb_array_elements(check_results) AS check_result
                WHERE status = 'ACCEPTED'
                  AND COALESCE((check_result->>'passed')::boolean, true) IS FALSE
                  AND check_result->>'severity' = 'CRITICAL'
                """
            )
        ).scalar()


def main():
    parser = argparse.ArgumentParser(
        description="Run and persist PS-5 validation for recipe_catalogue_v3."
    )
    parser.add_argument("--limit", type=int, default=100000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        json.dumps(
            validate_catalogue_v3(
                limit=args.limit,
                dry_run=args.dry_run,
            ),
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
