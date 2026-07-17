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
