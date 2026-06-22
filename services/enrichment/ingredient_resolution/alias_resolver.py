INGREDIENT_ALIAS = {

    # Wheat

    "atta": "whole_wheat_flour",

    "gehun atta": "whole_wheat_flour",

    "gothumai maavu": "whole_wheat_flour",

    "wheat flour": "whole_wheat_flour",


    # Chickpeas

    "kabuli chana": "chickpea",

    "kadala": "chickpea",

    "chole": "chickpea",


    # Gram Flour

    "besan": "gram_flour",

    "chickpea flour": "gram_flour",


    # Rice

    "sona masuri": "rice",

    "basmati": "rice",

    "basmati rice": "rice",


    # Lentils

    "toor dal": "pigeon_peas",

    "arhar dal": "pigeon_peas",

    "moong dal": "green_gram",

    "masoor dal": "red_lentil",

    "urad dal": "black_gram",


    # Dairy

    "paneer": "paneer",

    "curd": "yogurt",

    "dahi": "yogurt",


    # Spices

    "mirchi powder": "red_chili_powder",

    "haldi": "turmeric",

    "jeera": "cumin",

    "dhania": "coriander",

    "hing": "asafoetida",


    # Oils

    "ghee": "clarified_butter",

    "mustard oil": "mustard_oil",

    "groundnut oil": "peanut_oil"

}


def resolve_alias(name):

    key = name.lower().strip()

    return INGREDIENT_ALIAS.get(key)