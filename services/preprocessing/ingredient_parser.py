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
            "milligrams",
            "milligram",
            "pounds",
            "pound",
            "lbs",
            "lb",
            "ounces",
            "ounce",
            "oz",
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
            "packets",
            "packet",
            "blocks",
            "block",
            "portions",
            "portion",
            "slices",
            "slice",
            "leaves",
            "leaf",
            "roots",
            "root",
            "grams",
            "gram",
            "gm",
            "mg",
            "liters",
            "liter",
            "litres",
            "litre",
            "cups",
            "cup",
            "pcs",
            "pc",
            "nos",
            "tbsp",
            "tsp",
            "kg",
            "g",
            "ml",
            "l",
        ]

    def parse_quantity(self, raw_quantity):
        if raw_quantity is None:
            return None

        raw_quantity = self._normalize_fraction_text(raw_quantity).strip()

        if "+" in raw_quantity:
            values = [
                self.parse_quantity(part)
                for part in raw_quantity.split("+")
            ]
            values = [value for value in values if value is not None]

            if values:
                return sum(values)

        range_match = re.match(
            r"^(.+?)\s*(?:to|-)\s*(.+?)$",
            raw_quantity,
        )

        if range_match:
            values = [
                self.parse_quantity(range_match.group(1)),
                self.parse_quantity(range_match.group(2)),
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
        ingredient_text = self._normalize_compact_quantity_unit(ingredient_text)
        quantity = None
        remainder = ingredient_text
        quantity_match = re.match(
            r"^((?:\d+(?:\.\d+)?|\d+/\d+|[{}])"
            r"(?:\s*(?:to|-)\s*(?:\d+(?:\.\d+)?|\d+/\d+|[{}]))?"
            r"(?:\s*\+\s*(?:\d+(?:\.\d+)?|\d+/\d+|[{}]))*"
            r"(?:\s+(?:\d+/\d+|[{}]))?)\s+(.*)$".format(
                re.escape("".join(self.fraction_map.keys())),
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
        raw_ingredient_name = ingredient_name
        ingredient_name = self._clean_ingredient_name(ingredient_name)

        count_units = {
            "clove",
            "cloves",
            "leaf",
            "leaves",
            "piece",
            "pieces",
            "root",
            "roots",
            "slice",
            "slices",
            "sprig",
            "sprigs",
            "strand",
            "strands",
        }

        if unit in count_units and str(raw_ingredient_name or "").strip().startswith("("):
            ingredient_name = unit

        if not ingredient_name and unit in count_units:
            ingredient_name = unit

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

    def _normalize_compact_quantity_unit(self, value):
        value = str(value)
        quantity_pattern = r"(?:\d+(?:\.\d+)?|\d+/\d+)"

        value = re.sub(
            rf"^({quantity_pattern})\s*[\"“”]\s*",
            r"\1 inch ",
            value,
        )
        value = re.sub(
            rf"^({quantity_pattern})\s*-\s*(inch|inches)\b",
            r"\1 \2",
            value,
            flags=re.I,
        )

        compact_unit_match = re.match(
            rf"^({quantity_pattern})\s*([A-Za-z]+)\b(.*)$",
            value,
        )
        compact_units = {
            unit.lower()
            for unit in self.known_units
            if (len(unit) > 1 or unit == "g") and " " not in unit
        }

        if compact_unit_match:
            unit = compact_unit_match.group(2).lower()

            if unit in compact_units:
                return (
                    f"{compact_unit_match.group(1)} "
                    f"{unit}{compact_unit_match.group(3)}"
                ).strip()

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
        original_value = str(value or "")
        parenthetical = re.match(r"^\s*\(([^()]+)\)\s*$", original_value)

        if parenthetical:
            value = parenthetical.group(1)
        elif (
            original_value.lstrip().startswith("(")
            and " or " in original_value.lower()
        ):
            value = original_value.lstrip()[1:]

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
            "medium sized",
            "medium-sized",
            "organic",
            "plain",
            "processed",
            "pureed",
            "sliced",
            "small",
            "softened",
            "unsweetened",
        }
        changed = True

        while changed:
            changed = False

            for descriptor in descriptors:
                if value.lower().startswith(f"{descriptor} "):
                    value = value[len(descriptor):].strip()
                    changed = True

                if value.lower().endswith(f" {descriptor}"):
                    value = value[: -len(descriptor)].strip()
                    changed = True

        selected_alternate_measure = False

        if " or " in value.lower():
            options = re.split(r"\s+or\s+", value, maxsplit=1, flags=re.I)

            if self._is_measure_only(options[0]) and len(options) > 1:
                value = options[1]
                selected_alternate_measure = True
            else:
                value = options[0]

        if selected_alternate_measure:
            value = re.sub(r"^\s*\d+(?:\.\d+)?\s+", "", value).strip()

        changed = selected_alternate_measure

        while changed:
            changed = False

            for descriptor in descriptors:
                if value.lower().startswith(f"{descriptor} "):
                    value = value[len(descriptor):].strip()
                    changed = True

                if value.lower().endswith(f" {descriptor}"):
                    value = value[: -len(descriptor)].strip()
                    changed = True

        return value.strip()

    def _is_measure_only(self, value):
        units = "|".join(re.escape(unit) for unit in self.known_units)

        return bool(
            re.match(
                rf"^\s*(?:\d+(?:\.\d+)?|\d+/\d+)\s*(?:{units})\s*$",
                str(value or ""),
                flags=re.I,
            )
        )
