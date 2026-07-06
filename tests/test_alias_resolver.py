from services.enrichment.ingredient_resolution.alias_resolver import (
    normalize_ingredient_name,
    resolve_alias,
    resolve_alias_match,
)


def test_resolves_regional_aliases_to_canonical_names():
    assert resolve_alias("atta") == "whole_wheat_flour"
    assert resolve_alias("kadala") == "chickpea"
    assert resolve_alias("gehun ka atta") == "whole_wheat_flour"
    assert resolve_alias("gothumai maavu") == "whole_wheat_flour"
    assert resolve_alias("kadagu") == "mustard_seed"


def test_alias_resolution_normalizes_case_spacing_and_punctuation():
    assert normalize_ingredient_name("  GEHUN-KA   ATTA  ") == "gehun ka atta"
    assert resolve_alias("  GEHUN-KA   ATTA  ") == "whole_wheat_flour"


def test_resolves_common_scraped_recipe_aliases():
    assert resolve_alias("cumin seeds") == "cumin"
    assert resolve_alias("red chilli powder") == "red_chili_powder"
    assert resolve_alias("Kashmiri red chilli powder") == "red_chili_powder"
    assert resolve_alias("garlic cloves") == "garlic"
    assert resolve_alias("Pinch hing") == "asafoetida"
    assert resolve_alias("sea salt") == "salt"
    assert resolve_alias("water") == "water"
    assert resolve_alias("2 cloves ((optional))") == "clove"
    assert resolve_alias("Salt as needed") == "salt"
    assert resolve_alias("to 2 cups water") == "water"
    assert resolve_alias("medium tomatoes") == "tomato"


def test_alias_match_returns_resolution_metadata():
    match = resolve_alias_match("Besan")

    assert match == {
        "raw_name": "Besan",
        "normalized_name": "besan",
        "canonical_name": "gram_flour",
        "method": "alias",
        "tier": "exact_alias",
        "confidence_score": 1.0,
        "enrichment_flags": [],
    }


def test_unknown_alias_returns_none():
    assert resolve_alias("not a real ingredient") is None
    assert resolve_alias_match("not a real ingredient") is None
