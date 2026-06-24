LIQUID_INGREDIENTS = {

    "water",

    "milk",

    "oil",

    "ghee",

    "vinegar",

    "curd",

    "coconut_milk",

    "coconut milk"

}



def is_liquid(ingredient):

    ingredient = ingredient.lower().strip()
    ingredient = ingredient.replace(" ", "_")

    return ingredient in LIQUID_INGREDIENTS
