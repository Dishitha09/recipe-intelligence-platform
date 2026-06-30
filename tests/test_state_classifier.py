from services.enrichment.state.state_classifier import RecipeStateClassifier
from services.preprocessing.schema_models import Recipe


def build_recipe(title, description="", cuisine="Indian"):
    return Recipe(
        title=title,
        description=description,
        cuisine=cuisine,
        source_type="pytest",
        source_url="https://example.com/test",
        language="english",
        ingredients=[],
        steps=[],
    )


def test_state_classifier_detects_explicit_state_keyword():
    result = RecipeStateClassifier().classify(
        build_recipe("Gujarati Dhokla", "Steamed snack from Gujarat")
    )

    assert result.state == "Gujarat"
    assert result.region == "West"
    assert result.confidence >= 0.9


def test_state_classifier_detects_dish_keyword():
    result = RecipeStateClassifier().classify(
        build_recipe("Hyderabadi Bagara Rice")
    )

    assert result.state == "Telangana"
    assert result.region == "South"


def test_state_classifier_preserves_provided_state():
    recipe = build_recipe("Some Recipe").model_copy(
        update={"state": "Kerala"}
    )

    result = RecipeStateClassifier().classify(recipe)

    assert result.state == "Kerala"
    assert result.region == "South"
    assert result.method == "provided_state"


def test_state_classifier_returns_region_for_ambiguous_recipe():
    result = RecipeStateClassifier().classify(build_recipe("Plain Dosa"))

    assert result.state is None
    assert result.region == "South"
    assert result.method == "regional_keyword"
