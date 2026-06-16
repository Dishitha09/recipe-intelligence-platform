from services.preprocessing.schema_models import Recipe


def validate_recipe(recipe_data):

    try:

        recipe = Recipe(**recipe_data)

        return True, recipe

    except Exception as e:

        return False, str(e)