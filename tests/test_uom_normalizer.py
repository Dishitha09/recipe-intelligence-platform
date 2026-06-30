from services.enrichment.uom.uom_normalizer import UOMNormalizer
from services.enrichment.uom.ingredient_type import is_liquid


def test_density_conversion_for_solid_cup_to_grams():
    uom = UOMNormalizer()

    result = uom.normalize("flour", "1", "cup")

    assert result["canonical_quantity"] == 120
    assert result["canonical_unit"] == "g"
    assert result["conversion_method"] == "density_lookup"
    assert result["conversion_factor"] == 120


def test_volume_conversion_for_liquid_cup_to_ml():
    uom = UOMNormalizer()

    result = uom.normalize("milk", "1", "cup")

    assert result["canonical_quantity"] == 240
    assert result["canonical_unit"] == "ml"
    assert result["conversion_method"] == "volume_standard"


def test_imperial_weight_alias_converts_to_grams():
    uom = UOMNormalizer()

    result = uom.normalize("paneer", "2", "oz")

    assert result["canonical_quantity"] == 56.7
    assert result["canonical_unit"] == "g"


def test_colloquial_units_are_estimated_and_flagged():
    uom = UOMNormalizer()

    result = uom.normalize("spinach", "1", "handful")

    assert result["canonical_quantity"] == 30
    assert result["canonical_unit"] == "g"
    assert "colloquial_unit" in result["enrichment_flags"]


def test_unknown_units_are_flagged_without_crashing():
    uom = UOMNormalizer()

    result = uom.normalize("xyz", "1", "ladle")

    assert result["canonical_quantity"] is None
    assert result["canonical_unit"] is None
    assert "unit_unresolved" in result["enrichment_flags"]


def test_missing_unit_with_quantity_is_inferred_as_count():
    uom = UOMNormalizer()

    result = uom.normalize("green chili", "2", None)

    assert result["canonical_quantity"] == 2
    assert result["canonical_unit"] == "count"
    assert result["conversion_method"] == "count_inferred"


def test_solid_volume_without_density_passes_through_without_conflict():
    uom = UOMNormalizer()

    result = uom.normalize("unknown spice", "1", "tsp")

    assert result["canonical_quantity"] == 1
    assert result["canonical_unit"] == "tsp"
    assert result["conversion_method"] == "volume_passthrough_without_density"
    assert "uom_conflict" not in result["enrichment_flags"]


def test_common_dairy_liquids_are_classified_as_liquid():
    assert is_liquid("buttermilk") is True
    assert is_liquid("cream") is True
    assert is_liquid("plain yogurt") is True
