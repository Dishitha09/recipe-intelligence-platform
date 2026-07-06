import html
import re

from services.preprocessing.schema_models import Ingredient
from services.preprocessing.text_cleaner import clean_text


class IngredientParser:
    def __init__(self):
        self.fraction_map = {
            "\u00bc": 0.25,
            "\u00bd": 0.5,
            "\u00be": 0.75,
            "\u2153": 1 / 3,
            "\u2154": 2 / 3,
            "\u215b": 0.125,
            "\u215c": 0.375,
            "\u215d": 0.625,
            "\u215e": 0.875,
            "\ufffd": 0.5,
            "Â¼": 0.25,
            "Â½": 0.5,
            "Â¾": 0.75,
        }
        self.known_units = [
            "fluid ounces",
            "fluid ounce",
            "tablespoons",
            "tablespoon",
            "teaspoons",
            "teaspoon",
            "kilograms",
            "kilogram",
            "milliliters",
            "milliliter",
            "millilitres",
            "millilitre",
            "strands",
            "strand",
            "sprigs",
            "sprig",
            "inches",
            "inch",
            "cloves",
            "clove",
            "pieces",
            "piece",
            "slices",
            "slice",
            "grams",
            "gram",
            "cups",
            "cup",
            "tbsp",
            "tsp",
            "kg",
            "g",
            "ml",
        ]

    def parse_quantity(self, raw_quantity):
        if raw_quantity is None:
            return None

        raw_quantity = self._normalize_fraction_text(raw_quantity).strip()

        for separator in [" to ", " - "]:
            if separator in raw_quantity:
                values = [
                    self.parse_quantity(part)
                    for part in raw_quantity.split(separator, 1)
                ]
                values = [value for value in values if value is not None]

                if values:
                    return sum(values) / len(values)

        if raw_quantity in self.fraction_map:
            return self.fraction_map[raw_quantity]

        for fraction, value in self.fraction_map.items():
            if fraction in raw_quantity:
                whole = raw_quantity.replace(fraction, "").strip()

                if not whole:
                    return value

                try:
                    return float(whole) + value
                except ValueError:
                    return value

        parts = raw_quantity.split()

        if len(parts) == 2:
            try:
                whole = float(parts[0])
                fraction = self.parse_quantity(parts[1])

                if fraction is not None:
                    return whole + fraction
            except ValueError:
                return None

        if "/" in raw_quantity:
            try:
                numerator, denominator = raw_quantity.split("/", 1)

                return float(numerator) / float(denominator)
            except ValueError:
                return None

        try:
            return float(raw_quantity)
        except ValueError:
            return None

    def parse(self, ingredient_text):
        ingredient_text = clean_text(ingredient_text)
        ingredient_text = self._normalize_fraction_text(ingredient_text)
        quantity = None
        remainder = ingredient_text
        quantity_match = re.match(
            r"^((?:\d+(?:\.\d+)?|\d+/\d+|[{}])"
            r"(?:\s*(?:to|-)\s*(?:\d+(?:\.\d+)?|\d+/\d+|[{}]))?"
            r"(?:\s+(?:\d+/\d+|[{}]))?)\s+(.*)$".format(
                re.escape("".join(self.fraction_map.keys())),
                re.escape("".join(self.fraction_map.keys())),
                re.escape("".join(self.fraction_map.keys())),
            ),
            ingredient_text,
        )

        if quantity_match:
            quantity = self.parse_quantity(quantity_match.group(1))
            remainder = quantity_match.group(2)

        unit, ingredient_name = self._split_unit(remainder)
        ingredient_name = self._clean_ingredient_name(ingredient_name)

        if not ingredient_name:
            ingredient_name = ingredient_text

        return Ingredient(
            ingredient_name=ingredient_name,
            quantity=quantity,
            unit=unit,
            preparation=None,
        )

    def _normalize_fraction_text(self, value):
        value = str(value)

        for fraction in self.fraction_map:
            value = re.sub(
                rf"(\d)({re.escape(fraction)})",
                rf"\1 \2",
                value,
            )

        value = value.replace("\u2013", "-").replace("\u2014", "-")
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    def _split_unit(self, text):
        normalized = text.strip()
        lowered = normalized.lower()

        for unit in self.known_units:
            if lowered == unit:
                return unit, ""

            if lowered.startswith(f"{unit} "):
                return unit, normalized[len(unit):].strip()

        return None, normalized

    def _clean_ingredient_name(self, value):
        value = re.sub(r"\([^)]*\)", " ", value)
        value = value.replace("/", " ")
        value = re.sub(r"[^A-Za-z0-9_\-\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()

        descriptors = {
            "bone in",
            "boneless",
            "chopped",
            "dried",
            "fine",
            "fresh",
            "frozen",
            "grated",
            "ground",
            "hot",
            "large",
            "organic",
            "plain",
            "processed",
            "pureed",
            "small",
            "unsweetened",
        }
        changed = True

        while changed:
            changed = False

            for descriptor in descriptors:
                if value.lower().startswith(f"{descriptor} "):
                    value = value[len(descriptor):].strip()
                    changed = True

        if " or " in value.lower():
            value = re.split(r"\s+or\s+", value, maxsplit=1, flags=re.I)[0]

        return value.strip()
