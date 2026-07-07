import re
import unicodedata
from types import MappingProxyType


_WHITESPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"[_\-/,.;:()]+")
_LEADING_NOISE_RE = re.compile(
    r"^(?:"
    r"to\s+)?(?:\d+(?:\.\d+)?|\d+\s+to\s+\d+|\d+/\d+)"
    r"(?:\s+(?:cup|cups|teaspoon|teaspoons|tablespoon|tablespoons|"
    r"tsp|tbsp|gram|grams|kg|clove|cloves|inch|inches))?\s+"
)
_DESCRIPTOR_PREFIXES = (
    "bone in ",
    "boiled ",
    "crushed ",
    "full fat ",
    "large ",
    "medium ",
    "pinch ",
    "raw ",
    "small ",
    "thick ",
    "whole ",
)
_TRAILING_NOISE = {
    "as needed",
    "optional",
    "crushed",
    "laung",
}


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
    "mustard": "mustard_seed",
    "mustard seeds": "mustard_seed",
    "bay leaf": "bay_leaf",
    "bay leaves": "bay_leaf",
    "clove": "clove",
    "cloves": "clove",
    "green cardamom": "cardamom",
    "green cardamoms": "cardamom",
    "black cardamom": "cardamom",
    "cardamoms": "cardamom",
    "cinnamon piece": "cinnamon",
    "ceylon cinnamon piece": "cinnamon",
    "coriander seed": "coriander",
    "coriander seeds": "coriander",
    "fennel seeds": "fennel",
    "shahi jeera": "cumin",
    "cumin seed": "cumin",
    "cumin seeds": "cumin",
    "cumin powder": "cumin",
    "roasted cumin powder": "cumin",
    "dhania powder": "coriander",
    "coriander powder": "coriander",
    "red chili powder": "red_chili_powder",
    "red chilli powder": "red_chili_powder",
    "kashmiri red chilli powder": "red_chili_powder",
    "kashmiri chilli powder": "red_chili_powder",
    "kashmiri chili powder": "red_chili_powder",
    "chilli powder": "red_chili_powder",
    "chili powder": "red_chili_powder",
    "cardamom powder": "cardamom",
    "fennel powder": "fennel",
    "fennel seeds powder": "fennel",
    "fenugreek seed": "fenugreek",
    "fenugreek seeds": "fenugreek",
    "methi seed": "fenugreek",
    "methi seeds": "fenugreek",
    "garlic clove": "garlic",
    "garlic cloves": "garlic",
    "garlic paste": "garlic",
    "garlic powder": "garlic",
    "ginger paste": "dry_ginger",
    "ginger powder": "dry_ginger",
    "black pepper": "black_pepper",
    "black pepper corn": "black_pepper",
    "black peppercorn": "black_pepper",
    "black peppercorns": "black_pepper",
    "pepper": "black_pepper",
    "pepper corn": "black_pepper",
    "peppercorn": "black_pepper",
    "peppercorns": "black_pepper",
    "turmeric powder": "turmeric",
    "cashew nut": "cashew",
    "cashew nuts": "cashew",
    "cashews": "cashew",
    "whole cashews": "cashew",
    "almond": "almond",
    "almonds": "almond",
    "pistachios": "pistachio",
    "saffron": "saffron",
    "pinch saffron strands": "saffron",
    "all spice": "allspice",
    "all-spice": "allspice",
    "biryani masala powder": "biryani_masala",
    "biryani masala": "biryani_masala",
    "garam masala powder": "garam_masala",
    "amchur powder": "amchur_powder",
    "pepper powder": "black_pepper_powder",
    "black pepper powder": "black_pepper_powder",
    "green cardamom powder": "cardamom",
    "carom seeds": "carom_seeds",
    "ajwain": "carom_seeds",
    "chaat masala powder": "chaat_masala",
    "sambar powder": "sambar_powder",
    "nutmeg powder": "nutmeg_powder",
    "onion powder": "onion_powder",
    "italian herbs": "italian_herbs",

    # Oils and fats
    "ghee": "clarified_butter",
    "mustard oil": "mustard_oil",
    "groundnut oil": "peanut_oil",
    "oil": "oil",
    "olive oil": "olive_oil",
    "extra virgin olive oil": "extra_virgin_olive_oil",
    "unsalted butter": "butter",
    "melted butter": "butter",
    "oil for deep frying": "oil",
    "tbsps oil": "oil",
    "tbsps ghee": "clarified_butter",

    # Common vegetables and pantry staples
    "tomato": "tomato",
    "tomatoes": "tomato",
    "onion": "onion",
    "onions": "onion",
    "green chili": "green_chili",
    "green chilies": "green_chili",
    "green chilli": "green_chili",
    "green chillies": "green_chili",
    "green chili pepper": "green_chili",
    "green chili slit": "green_chili",
    "green chilies slit": "green_chili",
    "red chili": "red_chili",
    "red chilies": "red_chili",
    "red chilli": "red_chili",
    "red chillies": "red_chili",
    "red chili flakes": "red_chili_flakes",
    "bell pepper": "bell_pepper",
    "bell peppers": "bell_pepper",
    "red bell pepper": "bell_pepper",
    "kashmiri red chili powder": "red_chili_powder",
    "potato": "potato",
    "potatoes": "potato",
    "bhindi": "okra",
    "cauliflower": "cauliflower",
    "peanut": "peanut",
    "peanuts": "peanut",
    "roasted peanuts": "peanut",
    "lemon juice": "lemon",
    "ginger": "dry_ginger",
    "ginger grated": "dry_ginger",
    "ginger garlic paste": "dry_ginger",
    "ginger garlic": "dry_ginger",
    "curry leaf": "curry_leaves",
    "curry leaves": "curry_leaves",
    "rolled oats": "oats",
    "oat": "oats",
    "oats": "oats",
    "coconut": "coconut",
    "desiccated coconut": "desiccated_coconut",
    "coriander leaves": "coriander_leaves",
    "handful coriander leaves": "coriander_leaves",
    "coriander leaves chopped": "coriander_leaves",
    "coriander leaves cilantro": "coriander_leaves",
    "cilantro": "coriander_leaves",
    "spring onions": "spring_onions",
    "baby spinach": "baby_spinach",
    "methi leaves": "fenugreek_leaves",
    "lettuce leaves": "lettuce_leaves",
    "button mushrooms": "button_mushrooms",
    "white button mushrooms": "button_mushrooms",
    "soya chunks": "soya_chunks",
    "mutton": "mutton",
    "lamb": "mutton",
    "goat": "mutton",
    "bone in chicken": "chicken",
    "chicken": "chicken",
    "fish": "fish",
    "keema": "minced_meat",
    "plain yogurt": "yogurt",
    "greek yogurt": "yogurt",
    "heavy cream": "cream",
    "cream": "cream",
    "bread crumbs": "breadcrumbs",
    "bread slices": "bread_slices",
    "egg": "egg",
    "eggs": "egg",
    "boiled eggs": "egg",
    "hard boiled eggs": "egg",
    "egg white": "egg_white",
    "meat masala": "garam_masala",
    "garam masala": "garam_masala",
    "salt": "salt",
    "sea salt": "salt",
    "sugar": "sugar",
    "flour": "flour",
    "water": "water",
    "kewra water": "kewra_water",
    "rose water": "rose_water",
    "soya sauce": "soy_sauce",
    "soy sauce": "soy_sauce",
    "red chilli sauce": "chilli_sauce",
    "red chili sauce": "chilli_sauce",
    "tomato ketchup": "tomato_ketchup",
    "tomato sauce": "tomato_sauce",
    "tamarind chutney": "tamarind_chutney",
    "carrot": "carrot",
    "carrots": "carrot",
    "medium onion": "onion",
    "medium tomatoes": "tomato",
    "medium garlic": "garlic",
    "pinch hing": "asafoetida",
    "pinch asafoetida": "asafoetida",
    "pinch turmeric": "turmeric",
    "pinch urad dal": "black_gram",
    "asafoetida": "asafoetida",
    "clove optional": "clove",
    "cloves optional": "clove",
    "cinnamon stick": "cinnamon",
    "coconut milk": "coconut_milk",
    "thick coconut milk": "coconut_milk",
    "full fat milk": "milk",
    "whole milk": "milk",
    "liter milk": "milk",
    "milk powder": "milk_powder",
    "whipping cream": "whipping_cream",
    "roasted gram": "roasted_gram",
    "fried gram": "roasted_gram",
    "bengal gram": "chana_dal",
    "uncooked rice": "rice",
    "aged basmati rice": "aged_basmati_rice",
    "basmathi rice": "basmathi_rice",
    "thick poha": "poha",
    "dosa batter": "dosa_batter",
    "sweet corn kernels": "corn_kernels",
    "corn kernels": "corn_kernels",
    "ice cubes": "ice_cubes",
    "warm water": "warm_water",
    "chilled water": "chilled_water",
    "cold water": "cold_water",
    "cocoa powder": "cocoa_powder",
    "vanilla extract": "vanilla_extract",
    "apples": "apple",
    "oranges": "orange",
    "pomegranate arils": "pomegranate_arils",
    "toasted sesame seeds": "sesame_seeds",
    "black cardamoms": "black_cardamoms",
    "cinnamon sticks": "cinnamon_sticks",
    "cinnamon powder": "cinnamon_powder",
    "nylon sev": "sev",
    "mozzarella cheese": "mozzarella_cheese",
    "fish fillet": "fish_fillet",
    "chia seeds": "chia_seed",
}


INGREDIENT_ALIAS = MappingProxyType(
    {
        normalize_ingredient_name(alias): canonical_name
        for alias, canonical_name in _ALIASES.items()
    }
)


def resolve_alias_match(name):
    normalized_name = normalize_ingredient_name(name)
    canonical_name = None
    matched_name = normalized_name

    for candidate in _candidate_names(normalized_name):
        canonical_name = INGREDIENT_ALIAS.get(candidate)

        if canonical_name is not None:
            matched_name = candidate
            break

    if canonical_name is None:
        return None

    return {
        "raw_name": name,
        "normalized_name": matched_name,
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


def _candidate_names(normalized_name):
    candidates = []

    def add(value):
        value = _WHITESPACE_RE.sub(" ", str(value or "")).strip()
        if value and value not in candidates:
            candidates.append(value)

    add(normalized_name)

    stripped = normalized_name
    changed = True
    while changed:
        changed = False
        new_value = _LEADING_NOISE_RE.sub("", stripped).strip()

        if new_value != stripped:
            stripped = new_value
            add(stripped)
            changed = True

    for prefix in _DESCRIPTOR_PREFIXES:
        if stripped.startswith(prefix):
            add(stripped[len(prefix):])

    if stripped.endswith(" as needed"):
        add(stripped[: -len(" as needed")])

    tokens = [
        token
        for token in stripped.split()
        if token not in _TRAILING_NOISE
    ]
    add(" ".join(tokens))

    if re.search(r"\bcloves?\b", normalized_name):
        add("cloves")

    if len(tokens) > 1 and tokens[0] in {"lb", "lbs"}:
        add(" ".join(tokens[1:]))

    return candidates
