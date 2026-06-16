LIQUID_INGREDIENTS = {

    "water",

    "milk",

    "oil",

    "vinegar",

    "curd",

    "coconut_milk"

}



def is_liquid(ingredient):

    ingredient = ingredient.lower().strip()

    return ingredient in LIQUID_INGREDIENTS