LIQUID_INGREDIENTS = {

    "water",

    "milk",

    "oil",

    "ghee",

    "clarified_butter",

    "vinegar",

    "curd",

    "coconut_milk",

    "coconut milk",

    "buttermilk",

    "cream",

    "yogurt",

    "plain_yogurt",

    "curd",

}



def is_liquid(ingredient):

    ingredient = ingredient.lower().strip()
    ingredient = ingredient.replace(" ", "_")

    return (
        ingredient in LIQUID_INGREDIENTS
        or ingredient.endswith("_oil")
        or ingredient.endswith("_water")
        or ingredient.endswith("_milk")
        or ingredient.endswith("_vinegar")
    )
