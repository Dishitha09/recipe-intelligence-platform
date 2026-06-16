def check_title(recipe):

    return recipe.title is not None and recipe.title.strip() != ""



def check_ingredients(recipe):

    return len(recipe.ingredients) > 0



def check_source(recipe):

    return recipe.source_type is not None



def check_positive_quantity(ingredient):

    if ingredient.quantity is None:

        return False

    return ingredient.quantity > 0



def check_unit(unit):

    return unit in ["g","ml"]



def check_ingredient_name(name):

    return name is not None and name.strip() != ""