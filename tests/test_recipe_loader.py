from uuid import uuid4

import pytest
from sqlalchemy import text

from services.database.connection import engine
from services.database.recipe_loader import RecipeLoader
from services.database.validation_repository import ValidationRepository
from services.enrichment.recipe_enricher import RecipeEnricher
from services.preprocessing.schema_models import Ingredient, Recipe, RecipeStep
from services.validation.validation_engine import ValidationEngine


def require_database():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        pytest.skip(f"database unavailable: {exc}")


def cleanup_recipe(recipe_id):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM recipe_embeddings WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipe_steps WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipe_ingredients WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM validation_reports WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipes WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )


def build_enriched_recipe():
    recipe = Recipe(
        title=f"Integration Test Recipe {uuid4()}",
        description="Temporary recipe for DB integration tests",
        cuisine="Indian",
        source_type="pytest",
        source_url="https://example.com/integration-test",
        language="english",
        ingredients=[
            Ingredient(
                ingredient_name="rice",
                quantity=1,
                unit="cup",
            ),
            Ingredient(
                ingredient_name="paneer",
                quantity=1,
                unit="cup",
            ),
        ],
        steps=[
            RecipeStep(step_number=1, instruction="Prepare ingredients."),
            RecipeStep(step_number=2, instruction="Cook until done."),
        ],
        metadata={
            "images": ["https://cdn.example.com/test.jpg"],
            "nutrition": {"kcal_per_serving": 350},
        },
    )

    return RecipeEnricher().enrich_recipe(recipe)


def test_recipe_loader_persists_recipe_ingredients_steps_and_validation_report():
    require_database()
    recipe = build_enriched_recipe()
    report = ValidationEngine().validate(recipe)

    assert report.status == "ACCEPTED"

    loader = RecipeLoader()
    validation_repo = ValidationRepository()
    recipe_id = None

    try:
        recipe_id = loader.insert_recipe(recipe)
        loader.insert_ingredients(recipe_id, recipe.ingredients)
        loader.insert_steps(recipe_id, recipe.steps)
        validation_id = validation_repo.save_report(recipe_id, report)

        with engine.connect() as conn:
            ingredient_count = conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM recipe_ingredients
                    WHERE recipe_id=:recipe_id
                    """
                ),
                {"recipe_id": recipe_id},
            ).scalar()
            step_count = conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM recipe_steps
                    WHERE recipe_id=:recipe_id
                    """
                ),
                {"recipe_id": recipe_id},
            ).scalar()
            report_status = conn.execute(
                text(
                    """
                    SELECT status
                    FROM validation_reports
                    WHERE validation_id=:validation_id
                    """
                ),
                {"validation_id": validation_id},
            ).scalar()

        assert ingredient_count == 2
        assert step_count == 2
        assert report_status == "ACCEPTED"
    finally:
        if recipe_id is not None:
            cleanup_recipe(recipe_id)


def test_validation_repository_persists_review_and_dead_letter_records():
    require_database()
    recipe = build_enriched_recipe().model_copy(
        update={
            "ingredients": [
                Ingredient(
                    ingredient_name="flour",
                    quantity=1,
                    unit="cup",
                    canonical_name="flour",
                    resolution_confidence=1.0,
                    canonical_quantity=240,
                    canonical_unit="ml",
                    conversion_method="volume_without_density",
                    uom_confidence_score=0.55,
                    enrichment_flags=["uom_conflict"],
                ),
                Ingredient(
                    ingredient_name="water",
                    quantity=1,
                    unit="cup",
                    canonical_name="water",
                    resolution_confidence=1.0,
                    canonical_quantity=240,
                    canonical_unit="ml",
                    conversion_method="volume_standard",
                    uom_confidence_score=1.0,
                ),
            ]
        }
    )
    report = ValidationEngine().validate(recipe)
    record_id = str(uuid4())
    repo = ValidationRepository()

    review_id = repo.save_review(record_id, recipe, report)
    dlq_id = repo.save_dead_letter(
        source_type="pytest",
        record_id=record_id,
        raw_payload={"record_id": record_id},
        error_message="integration dead letter",
        validation_report=report.model_dump(mode="json"),
    )

    try:
        with engine.connect() as conn:
            review_status = conn.execute(
                text(
                    """
                    SELECT status
                    FROM review_queue
                    WHERE review_id=:review_id
                    """
                ),
                {"review_id": review_id},
            ).scalar()
            dead_letter_message = conn.execute(
                text(
                    """
                    SELECT error_message
                    FROM dead_letter_queue
                    WHERE dlq_id=:dlq_id
                    """
                ),
                {"dlq_id": dlq_id},
            ).scalar()

        assert review_status == "PENDING"
        assert dead_letter_message == "integration dead letter"
    finally:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM review_queue WHERE review_id=:review_id"),
                {"review_id": review_id},
            )
            conn.execute(
                text("DELETE FROM dead_letter_queue WHERE dlq_id=:dlq_id"),
                {"dlq_id": dlq_id},
            )
