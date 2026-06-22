import re

from services.preprocessing.schema_models import Ingredient


class IngredientParser:

    def __init__(self):

        self.fraction_map = {

            "¼": 0.25,
            "½": 0.5,
            "¾": 0.75,
            "⅓": 0.33,
            "⅔": 0.66,
            "⅛": 0.125,
            "⅜": 0.375,
            "⅝": 0.625,
            "⅞": 0.875

        }

    def parse_quantity(self, raw_quantity):

        if raw_quantity is None:

            return None

        raw_quantity = raw_quantity.strip()

        try:

            if raw_quantity in self.fraction_map:

                return self.fraction_map[raw_quantity]

            for frac, val in self.fraction_map.items():

                if frac in raw_quantity:

                    whole = raw_quantity.replace(frac, "").strip()

                    if whole == "":

                        return val

                    return float(whole) + val

            if "/" in raw_quantity:

                a, b = raw_quantity.split("/")

                return float(a) / float(b)

            return float(raw_quantity)

        except:

            return None

    def parse(self, ingredient_text):

        ingredient_text = ingredient_text.strip()

        pattern = r"^([\d\.\/¼½¾⅓⅔⅛⅜⅝⅞]*)\s*([a-zA-Z]+)?\s*(.*)$"

        match = re.match(

            pattern,

            ingredient_text

        )

        if match:

            raw_quantity = match.group(1)

            quantity = self.parse_quantity(

                raw_quantity

            )

            unit = match.group(2)

            ingredient_name = match.group(3)

            return Ingredient(

                ingredient_name=ingredient_name.strip(),

                quantity=quantity,

                unit=unit,

                preparation=None

            )

        return Ingredient(

            ingredient_name=ingredient_text,

            quantity=None,

            unit=None,

            preparation=None

        )