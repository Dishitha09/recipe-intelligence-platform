from services.database.fingerprints import recipe_fingerprints, stable_hash
from services.preprocessing.schema_models import Ingredient, Recipe, RecipeStep


def build_recipe(step_text="Cook rice."):
    return Recipe(
        title="Tomato Rice",
        description="A quick rice dish",
        cuisine="Indian",
        source_type="pytest",
        source_url=" HTTPS://Example.com/Tomato-Rice ",
        language="english",
        ingredients=[
            Ingredient(ingredient_name="rice", quantity=200, unit="g"),
            Ingredient(ingredient_name="tomato", quantity=150, unit="g"),
        ],
        steps=[RecipeStep(step_number=1, instruction=step_text)],
        metadata={"record_id": "volatile"},
    )


def test_recipe_fingerprint_is_stable_for_same_recipe_content():
    first = recipe_fingerprints(build_recipe())
    second = recipe_fingerprints(
        build_recipe().model_copy(update={"metadata": {"record_id": "changed"}})
    )

    assert first == second


def test_recipe_fingerprint_changes_when_cooking_steps_change():
    first = recipe_fingerprints(build_recipe("Cook rice."))
    second = recipe_fingerprints(build_recipe("Fry rice with tomato."))

    assert first["source_url_hash"] == second["source_url_hash"]
    assert first["content_hash"] != second["content_hash"]


def test_stable_hash_ignores_volatile_keys():
    first = stable_hash({"record_id": "one", "value": "same"})
    second = stable_hash({"record_id": "two", "value": "same"})

    assert first == second
