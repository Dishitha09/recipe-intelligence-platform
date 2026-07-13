from services.preprocessing.schema_models import Recipe
from services.preprocessing.schema_registry import SchemaRegistry


def validate_recipe(recipe_data):

    try:

        recipe = Recipe(**recipe_data)
        registry_result = SchemaRegistry().validate(
            recipe.model_dump(mode="json"),
            version=recipe.schema_version,
        )

        if not registry_result["valid"]:
            return False, registry_result["errors"]

        return True, recipe

    except Exception as e:

        return False, str(e)
