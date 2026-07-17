from services.preprocessing.ingredient_parser import IngredientParser


def test_ingredient_parser_handles_unicode_fractions_and_units():
    parser = IngredientParser()

    result = parser.parse("1\u00bd cup rolled oats")

    assert result.quantity == 1.5
    assert result.unit == "cup"
    assert result.ingredient_name == "rolled oats"


def test_ingredient_parser_handles_ranges_and_parenthetical_notes():
    parser = IngredientParser()

    result = parser.parse("2 to 3 (1 gram) bay leaves")

    assert result.quantity == 2.5
    assert result.unit is None
    assert result.ingredient_name == "bay leaves"


def test_ingredient_parser_strips_preparation_noise():
    parser = IngredientParser()

    result = parser.parse("1 cup grated coconut (fresh or frozen)")

    assert result.quantity == 1
    assert result.unit == "cup"
    assert result.ingredient_name == "coconut"


def test_ingredient_parser_recognizes_imperial_weight_units():
    parser = IngredientParser()

    result = parser.parse("6 to 8 oz sliced white mushrooms")

    assert result.quantity == 7
    assert result.unit == "oz"
    assert result.ingredient_name == "white mushrooms"


def test_ingredient_parser_splits_compact_metric_quantity_units():
    parser = IngredientParser()

    result = parser.parse("300g All-purpose flour (maida)")

    assert result.quantity == 300
    assert result.unit == "g"
    assert result.ingredient_name == "All-purpose flour"


def test_ingredient_parser_splits_compact_count_units():
    parser = IngredientParser()

    result = parser.parse("4piece Eggs")

    assert result.quantity == 4
    assert result.unit == "piece"
    assert result.ingredient_name == "Eggs"


def test_ingredient_parser_converts_inch_mark_to_unit():
    parser = IngredientParser()

    result = parser.parse('1" ginger (peeled)')

    assert result.quantity == 1
    assert result.unit == "inch"
    assert result.ingredient_name == "ginger"


def test_ingredient_parser_handles_no_space_ranges():
    parser = IngredientParser()

    result = parser.parse("2-3 cloves (laung)")

    assert result.quantity == 2.5
    assert result.unit == "cloves"
    assert result.ingredient_name == "cloves"


def test_ingredient_parser_splits_compact_gm_unit():
    parser = IngredientParser()

    result = parser.parse("180gm maida / plain flour")

    assert result.quantity == 180
    assert result.unit == "gm"
    assert result.ingredient_name == "maida plain flour"


def test_ingredient_parser_handles_parenthetical_only_item():
    parser = IngredientParser()

    result = parser.parse("3 tablespoons (warm water)")

    assert result.quantity == 3
    assert result.unit == "tablespoons"
    assert result.ingredient_name == "warm water"


def test_ingredient_parser_handles_hyphenated_inch_unit():
    parser = IngredientParser()

    result = parser.parse("1-inch piece of cinnamon stick (dalchini)")

    assert result.quantity == 1
    assert result.unit == "inch"
    assert result.ingredient_name == "piece of cinnamon stick"


def test_ingredient_parser_sums_plus_fraction_quantity():
    parser = IngredientParser()

    result = parser.parse("3/4+1/4 Hung Curd (Greek Yogurt)")

    assert result.quantity == 1
    assert result.unit is None
    assert result.ingredient_name == "Hung Curd"


def test_ingredient_parser_uses_non_measure_or_option():
    parser = IngredientParser()

    result = parser.parse("1 cup (150 grams or 2 medium-sized tomatoes (- chopped)")

    assert result.quantity == 1
    assert result.unit == "cup"
    assert result.ingredient_name == "tomatoes"
