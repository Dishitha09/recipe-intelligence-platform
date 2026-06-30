import json
import tempfile

from services.preprocessing.schema_models import Ingredient, Recipe, RecipeStep
from services.validation.validation_engine import ValidationEngine


def build_recipe(**overrides):
    data = {
        "title": "Masala Dosa",
        "description": "South Indian breakfast",
        "cuisine": "South Indian",
        "source_type": "web",
        "source_url": "https://example.com/masala-dosa",
        "language": "english",
        "ingredients": [
            Ingredient(
                ingredient_name="rice",
                quantity=1,
                unit="cup",
                canonical_name="rice",
                resolution_method="alias",
                resolution_tier="exact_alias",
                resolution_confidence=1.0,
                canonical_quantity=200,
                canonical_unit="g",
                conversion_method="density_lookup",
                uom_confidence_score=0.95,
            ),
            Ingredient(
                ingredient_name="urad dal",
                quantity=1,
                unit="cup",
                canonical_name="black_gram",
                resolution_method="alias",
                resolution_tier="exact_alias",
                resolution_confidence=1.0,
                canonical_quantity=190,
                canonical_unit="g",
                conversion_method="density_lookup",
                uom_confidence_score=0.95,
            ),
        ],
        "steps": [
            RecipeStep(step_number=1, instruction="Soak rice and dal."),
            RecipeStep(step_number=2, instruction="Grind and cook."),
        ],
        "metadata": {
            "images": ["https://cdn.example.com/dosa.jpg"],
            "nutrition": {"kcal_per_serving": 350},
        },
    }
    data.update(overrides)

    return Recipe(**data)


def test_validation_accepts_clean_enriched_recipe():
    report = ValidationEngine().validate(build_recipe())

    assert report.status == "ACCEPTED"
    assert len(report.check_results) == 11
    assert all(result.passed for result in report if result.check_id != "V11")


def test_validation_rejects_critical_schema_failures():
    recipe = build_recipe(steps=[])

    report = ValidationEngine().validate(recipe)

    assert report.status == "REJECTED"
    assert any(
        result.check_id == "V01" and not result.passed
        for result in report
    )


def test_validation_allows_single_ingredient_preparations():
    recipe = build_recipe(
        ingredients=[
            Ingredient(
                ingredient_name="cumin",
                quantity=1,
                unit="cup",
                canonical_name="cumin",
                resolution_confidence=1.0,
                canonical_quantity=1,
                canonical_unit="cup",
                conversion_method="volume_passthrough_without_density",
                uom_confidence_score=0.75,
            )
        ]
    )

    report = ValidationEngine().validate(recipe)

    assert not any(
        result.check_id == "V02" and not result.passed
        for result in report
    )


def test_validation_routes_high_failures_to_review():
    recipe = build_recipe(
        ingredients=[
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
    )

    report = ValidationEngine().validate(recipe)

    assert report.status == "REVIEW"
    assert any(
        result.check_id == "V06" and not result.passed
        for result in report
    )


def test_validation_checks_can_be_disabled_by_config():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as file:
        json.dump({"checks": {"V08": {"enabled": False}}}, file)
        config_path = file.name

    recipe = build_recipe(
        ingredients=[
            Ingredient(
                ingredient_name="mystery",
                quantity=1,
                unit="cup",
                canonical_name=None,
                resolution_confidence=0.0,
                enrichment_flags=["unresolved_ingredient"],
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
    )

    report = ValidationEngine(config_path=config_path).validate(recipe)

    assert not any(result.check_id == "V08" for result in report)
