from services.enrichment.uom.uom_normalizer import UOMNormalizer


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
