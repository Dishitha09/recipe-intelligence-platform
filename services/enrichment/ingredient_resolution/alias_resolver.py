import re
import unicodedata
from types import MappingProxyType


_WHITESPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"[_\-/,.;:()]+")


def normalize_ingredient_name(name):
    if name is None:
        return ""

    normalized = unicodedata.normalize("NFKC", str(name))
    normalized = normalized.lower()
    normalized = _SEPARATOR_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)

    return normalized.strip()


_ALIASES = {
    # Wheat
    "atta": "whole_wheat_flour",
    "gehun atta": "whole_wheat_flour",
    "gehun ka atta": "whole_wheat_flour",
    "chakki atta": "whole_wheat_flour",
    "chakki ka atta": "whole_wheat_flour",
    "gothumai maavu": "whole_wheat_flour",
    "wheat flour": "whole_wheat_flour",
    "whole wheat flour": "whole_wheat_flour",
    "ww flour": "whole_wheat_flour",

    # Chickpeas
    "kabuli chana": "chickpea",
    "kadala": "chickpea",
    "kondakadalai": "chickpea",
    "chole": "chickpea",
    "chana": "chickpea",
    "chickpea": "chickpea",
    "chickpeas": "chickpea",

    # Gram Flour
    "besan": "gram_flour",
    "chickpea flour": "gram_flour",
    "gram flour": "gram_flour",

    # Rice
    "sona masuri": "rice",
    "basmati": "rice",
    "basmati rice": "rice",
    "rice": "rice",
    "arisi": "rice",
    "chawal": "rice",

    # Lentils
    "toor dal": "pigeon_peas",
    "pigeon peas": "pigeon_peas",
    "pigeon_peas": "pigeon_peas",
    "tuvar dal": "pigeon_peas",
    "arhar dal": "pigeon_peas",
    "moong dal": "green_gram",
    "green gram": "green_gram",
    "green_gram": "green_gram",
    "masoor dal": "red_lentil",
    "red lentil": "red_lentil",
    "red_lentil": "red_lentil",
    "urad dal": "black_gram",
    "black gram": "black_gram",
    "black_gram": "black_gram",

    # Dairy
    "paneer": "paneer",
    "curd": "yogurt",
    "dahi": "yogurt",
    "yoghurt": "yogurt",
    "yogurt": "yogurt",
    "milk": "milk",
    "butter": "butter",

    # Spices
    "mirchi powder": "red_chili_powder",
    "lal mirch": "red_chili_powder",
    "haldi": "turmeric",
    "jeera": "cumin",
    "dhania": "coriander",
    "hing": "asafoetida",
    "kadugu": "mustard_seed",
    "kadagu": "mustard_seed",
    "rai": "mustard_seed",

    # Oils and fats
    "ghee": "clarified_butter",
    "mustard oil": "mustard_oil",
    "groundnut oil": "peanut_oil",
    "oil": "oil",

    # Common vegetables and pantry staples
    "tomato": "tomato",
    "tomatoes": "tomato",
    "onion": "onion",
    "onions": "onion",
    "potato": "potato",
    "potatoes": "potato",
    "cauliflower": "cauliflower",
    "salt": "salt",
    "sugar": "sugar",
    "flour": "flour",
}


INGREDIENT_ALIAS = MappingProxyType(
    {
        normalize_ingredient_name(alias): canonical_name
        for alias, canonical_name in _ALIASES.items()
    }
)


def resolve_alias_match(name):
    normalized_name = normalize_ingredient_name(name)
    canonical_name = INGREDIENT_ALIAS.get(normalized_name)

    if canonical_name is None:
        return None

    return {
        "raw_name": name,
        "normalized_name": normalized_name,
        "canonical_name": canonical_name,
        "method": "alias",
        "tier": "exact_alias",
        "confidence_score": 1.0,
        "enrichment_flags": [],
    }


def resolve_alias(name):
    match = resolve_alias_match(name)

    if match is None:
        return None

    return match["canonical_name"]
