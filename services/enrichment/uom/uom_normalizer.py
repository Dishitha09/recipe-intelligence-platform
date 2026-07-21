import re
from fractions import Fraction

from services.enrichment.uom.density_table import DENSITY
from services.enrichment.uom.ingredient_type import is_liquid


CANONICAL_UNITS = {"g", "ml", "tsp", "tbsp", "cup", "count"}

LIQUIDS = {
    "buttermilk",
    "coconut milk",
    "coconut_milk",
    "cream",
    "curd drink",
    "ghee",
    "clarified_butter",
    "milk",
    "oil",
    "vinegar",
    "water",
}

GENERIC_SOLID_DENSITY_G_PER_CUP = 120.0


class UOMNormalizer:
    def __init__(self):
        self.weight_units = {
            "g": ("g", 1.0),
            "gm": ("g", 1.0),
            "gram": ("g", 1.0),
            "grams": ("g", 1.0),
            "kg": ("g", 1000.0),
            "kilogram": ("g", 1000.0),
            "kilograms": ("g", 1000.0),
            "mg": ("g", 0.001),
            "milligram": ("g", 0.001),
            "milligrams": ("g", 0.001),
            "oz": ("g", 28.3495),
            "ounce": ("g", 28.3495),
            "ounces": ("g", 28.3495),
            "lb": ("g", 453.592),
            "lbs": ("g", 453.592),
            "pound": ("g", 453.592),
            "pounds": ("g", 453.592),
        }
        self.volume_units = {
            "ml": ("ml", 1.0),
            "milliliter": ("ml", 1.0),
            "milliliters": ("ml", 1.0),
            "millilitre": ("ml", 1.0),
            "millilitres": ("ml", 1.0),
            "l": ("ml", 1000.0),
            "liter": ("ml", 1000.0),
            "liters": ("ml", 1000.0),
            "litre": ("ml", 1000.0),
            "litres": ("ml", 1000.0),
            "fl oz": ("ml", 29.5735),
            "fluid ounce": ("ml", 29.5735),
            "fluid ounces": ("ml", 29.5735),
            "t": ("tsp", 5.0),
            "tsp": ("tsp", 5.0),
            "teaspoon": ("tsp", 5.0),
            "teaspoons": ("tsp", 5.0),
            "tbsp": ("tbsp", 15.0),
            "tablespoon": ("tbsp", 15.0),
            "tablespoons": ("tbsp", 15.0),
            "c": ("cup", 240.0),
            "cup": ("cup", 240.0),
            "cups": ("cup", 240.0),
            "cupful": ("cup", 240.0),
            "cup full": ("cup", 240.0),
            "glass": ("cup", 250.0),
            "katori": ("cup", 150.0),
            "bowl": ("cup", 300.0),
        }
        self.count_units = {
            "count",
            "piece",
            "pieces",
            "pc",
            "pcs",
            "packet",
            "packets",
            "block",
            "blocks",
            "number",
            "nos",
            "clove",
            "cloves",
            "slice",
            "slices",
            "inch",
            "inches",
            "leaf",
            "leaves",
            "portion",
            "portions",
            "root",
            "roots",
            "sprig",
            "sprigs",
            "strand",
            "strands",
        }
        self.colloquial_units = {
            "pinch": ("g", 0.3, 0.8),
            "pinches": ("g", 0.3, 0.8),
            "handful": ("g", 30.0, 0.7),
            "handfuls": ("g", 30.0, 0.7),
        }
        self.unquantified_units = {
            "as needed",
            "as required",
            "to taste",
            "taste",
            "a squeeze",
            "squeeze",
        }

    def parse_quantity(self, value):
        if value is None:
            return None

        value = str(value).strip().lower()

        if value in {"", "none", "nan"}:
            return None

        value = value.replace("half", "1/2")
        value = value.replace("quarter", "1/4")

        try:
            return float(value)
        except ValueError:
            pass

        try:
            return float(Fraction(value))
        except ValueError:
            pass

        parts = value.split()

        if len(parts) == 2:
            try:
                return float(parts[0]) + float(Fraction(parts[1]))
            except ValueError:
                return None

        return None

    def _round_quantity(self, value):
        if value is None:
            return None

        rounded = round(float(value), 2)

        if rounded.is_integer():
            return int(rounded)

        return rounded

    def normalize(self, ingredient_name, quantity_str, unit_str):
        ingredient_key = self._ingredient_key(ingredient_name)
        raw_unit = self._normalize_unit(unit_str)
        quantity = self.parse_quantity(quantity_str)

        if raw_unit in self.unquantified_units:
            return self._result(
                ingredient_name,
                quantity,
                raw_unit,
                None,
                None,
                "unquantified",
                0.5,
                flags=["unquantified_unit"],
            )

        if quantity is None:
            return self._result(
                ingredient_name,
                None,
                raw_unit,
                None,
                None,
                "unknown",
                0.0,
                flags=["quantity_missing"],
            )

        if raw_unit == "":
            return self._result(
                ingredient_name,
                quantity,
                raw_unit,
                quantity,
                "count",
                "count_inferred",
                0.8,
                conversion_factor=1.0,
            )

        if raw_unit in self.weight_units:
            canonical_unit, factor = self.weight_units[raw_unit]
            return self._result(
                ingredient_name,
                quantity,
                raw_unit,
                round(quantity * factor, 2),
                canonical_unit,
                "weight_standard",
                1.0,
                conversion_factor=factor,
            )

        if raw_unit in self.colloquial_units:
            canonical_unit, factor, confidence = self.colloquial_units[raw_unit]
            return self._result(
                ingredient_name,
                quantity,
                raw_unit,
                round(quantity * factor, 2),
                canonical_unit,
                "colloquial_estimate",
                confidence,
                conversion_factor=factor,
                flags=["colloquial_unit"],
            )

        if raw_unit in self.count_units:
            return self._result(
                ingredient_name,
                quantity,
                raw_unit,
                quantity,
                "count",
                "count_passthrough",
                1.0,
                conversion_factor=1.0,
            )

        if raw_unit in self.volume_units:
            normalized_volume_unit, ml_factor = self.volume_units[raw_unit]
            ml = quantity * ml_factor

            if ingredient_key in LIQUIDS or is_liquid(ingredient_key):
                return self._result(
                    ingredient_name,
                    quantity,
                    normalized_volume_unit,
                    round(ml, 2),
                    "ml",
                    "volume_standard",
                    1.0,
                    conversion_factor=ml_factor,
                )

            density = self._density_for(ingredient_key)

            if density is not None:
                grams_per_ml = density / 240.0
                grams = ml * grams_per_ml
                return self._result(
                    ingredient_name,
                    quantity,
                    normalized_volume_unit,
                    round(grams, 2),
                    "g",
                    "density_lookup",
                    0.95,
                    conversion_factor=round(grams / quantity, 4),
                )

            grams_per_ml = GENERIC_SOLID_DENSITY_G_PER_CUP / 240.0
            grams = ml * grams_per_ml
            return self._result(
                ingredient_name,
                quantity,
                normalized_volume_unit,
                round(grams, 2),
                "g",
                "estimated_density_lookup",
                0.7,
                conversion_factor=round(grams / quantity, 4),
                flags=["density_estimated"],
            )

        return self._result(
            ingredient_name,
            quantity,
            raw_unit,
            None,
            None,
            "unknown",
            0.0,
            flags=["unit_unresolved"],
        )

    def _normalize_unit(self, unit):
        if unit is None:
            return ""

        normalized = str(unit).strip().lower()
        normalized = normalized.replace(".", "")
        normalized = normalized.replace("-", " ")
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized

    def _ingredient_key(self, ingredient_name):
        return str(ingredient_name or "").lower().strip().replace("_", " ")

    def _density_for(self, ingredient_key):
        if ingredient_key in DENSITY:
            return DENSITY[ingredient_key]

        compact = ingredient_key.replace("_", " ")

        if compact in DENSITY:
            return DENSITY[compact]

        aliases = {
            "whole wheat flour": "wheat flour",
            "gram flour": "besan",
            "chickpea": "chickpeas",
            "pigeon peas": "toor dal",
            "green gram": "moong dal",
            "clarified butter": "ghee",
        }
        alias = aliases.get(compact)

        if alias:
            return DENSITY.get(alias)

        words = compact.split()
        descriptor_words = {
            "black",
            "brown",
            "diced",
            "green",
            "raw",
            "red",
            "ripe",
            "sliced",
            "small",
            "sweet",
            "white",
            "yellow",
        }
        stripped = " ".join(word for word in words if word not in descriptor_words)

        if stripped in DENSITY:
            return DENSITY[stripped]

        for key, density in DENSITY.items():
            if compact.endswith(f" {key}") or stripped.endswith(f" {key}"):
                return density

        return None

    def _result(
        self,
        ingredient_name,
        quantity,
        unit,
        canonical_quantity,
        canonical_unit,
        conversion_method,
        confidence_score,
        conversion_factor=None,
        flags=None,
    ):
        return {
            "ingredient_name": ingredient_name,
            "quantity": self._round_quantity(quantity),
            "unit": unit,
            "raw_unit": unit,
            "canonical_quantity": self._round_quantity(canonical_quantity),
            "canonical_unit": canonical_unit,
            "conversion_method": conversion_method,
            "conversion_factor": self._round_quantity(conversion_factor),
            "confidence_score": confidence_score,
            "enrichment_flags": flags or [],
        }
