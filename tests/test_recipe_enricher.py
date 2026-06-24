from services.enrichment.recipe_enricher import RecipeEnricher
from services.enrichment.ingredient_resolution.ingredient_resolver import (
    IngredientResolver,
)
from services.preprocessing.schema_models import Ingredient, Recipe, RecipeStep


def test_recipe_enricher_adds_resolution_and_uom_metadata():
    recipe = Recipe(
        title="Atta Roti",
        cuisine="Indian",
        source_type="text",
        source_url="https://example.com/roti",
        language="english",
        ingredients=[
            Ingredient(
                ingredient_name="atta",
                quantity=1,
                unit="cup",
            ),
            Ingredient(
                ingredient_name="milk",
                quantity=1,
                unit="cup",
            ),
        ],
        steps=[
            RecipeStep(step_number=1, instruction="Mix and cook.")
        ],
    )

    enriched = RecipeEnricher(
        ingredient_resolver=IngredientResolver(use_database=False)
    ).enrich_recipe(recipe)

    flour = enriched.ingredients[0]
    milk = enriched.ingredients[1]

    assert flour.canonical_name == "whole_wheat_flour"
    assert flour.resolution_method == "alias"
    assert flour.canonical_quantity == 120
    assert flour.canonical_unit == "g"
    assert milk.canonical_quantity == 240
    assert milk.canonical_unit == "ml"
    assert enriched.metadata["enrichment"]["ingredient_resolution_rate"] == 1.0
