INGREDIENT_ALIAS = {

    "atta": "whole_wheat_flour",

    "gehun atta": "whole_wheat_flour",

    "kadala": "chickpea",

    "kabuli chana": "chickpea",

    "besan": "gram_flour",

    "gothumai maavu": "whole_wheat_flour",

    "paneer": "paneer"

}


def resolve_alias(name):

    key = name.lower().strip()

    return INGREDIENT_ALIAS.get(key, None)