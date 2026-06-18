from fractions import Fraction

from services.enrichment.uom.density_table import DENSITY


LIQUIDS = {

    "milk",

    "water",

    "oil",

    "ghee",

    "coconut milk",

    "buttermilk",

    "cream",

    "curd drink"

}


class UOMNormalizer:


    def __init__(self):


        self.volume_units = {

            "cup":240,

            "tbsp":15,

            "tablespoon":15,

            "tsp":5,

            "teaspoon":5,

            "glass":250,

            "katori":150,

            "bowl":300

        }


        self.weight_units = {

            "g":1,

            "gm":1,

            "gram":1,

            "grams":1,

            "kg":1000,

            "mg":0.001

        }



    def parse_quantity(self,value):


        value=str(value).strip()


        try:

            return float(value)


        except:


            try:

                return float(Fraction(value))


            except:

                return None



    def normalize(


        self,

        ingredient_name,

        quantity_str,

        unit_str

    ):


        ingredient=ingredient_name.lower().strip()

        unit=unit_str.lower().strip()


        quantity=self.parse_quantity(

            quantity_str

        )


        if quantity is None:


            return {


                "ingredient_name":ingredient_name,

                "quantity":None,

                "unit":unit_str,

                "canonical_quantity":None,

                "canonical_unit":None,

                "conversion_method":"unknown",

                "confidence_score":0.0

            }


        # weight passthrough

        if unit in self.weight_units:


            grams=quantity*self.weight_units[unit]


            return {


                "ingredient_name":ingredient_name,

                "quantity":quantity,

                "unit":unit,


                "canonical_quantity":round(

                    grams,

                    2

                ),


                "canonical_unit":"g",


                "conversion_method":

                "weight_passthrough",


                "confidence_score":1.0

            }


        # pinch

        if unit=="pinch":


            return {


                "ingredient_name":ingredient_name,

                "quantity":quantity,

                "unit":"pinch",


                "canonical_quantity":0.3*quantity,


                "canonical_unit":"g",


                "conversion_method":"indian_unit",


                "confidence_score":0.8

            }


        # handful

        if unit=="handful":


            return {


                "ingredient_name":ingredient_name,

                "quantity":quantity,

                "unit":"handful",


                "canonical_quantity":30*quantity,


                "canonical_unit":"g",


                "conversion_method":"indian_unit",


                "confidence_score":0.7

            }


        # liquids

        if ingredient in LIQUIDS:


            if unit in self.volume_units:


                ml=quantity*self.volume_units[unit]


                return {


                    "ingredient_name":ingredient_name,

                    "quantity":quantity,

                    "unit":unit,


                    "canonical_quantity":

                    round(ml,2),


                    "canonical_unit":"ml",


                    "conversion_method":

                    "volume_standard",


                    "confidence_score":1.0

                }


        # solids

        if ingredient in DENSITY:


            if unit=="cup":


                grams=quantity*DENSITY[ingredient]


            elif unit=="katori":


                grams=(

                    quantity

                    *

                    DENSITY[ingredient]

                    *

                    (150/240)

                )


            elif unit=="bowl":


                grams=(

                    quantity

                    *

                    DENSITY[ingredient]

                    *

                    (300/240)

                )


            else:


                return {


                    "ingredient_name":ingredient_name,

                    "quantity":quantity,

                    "unit":unit,


                    "canonical_quantity":None,


                    "canonical_unit":None,


                    "conversion_method":"unknown",


                    "confidence_score":0.0

                }


            return {


                "ingredient_name":ingredient_name,

                "quantity":quantity,

                "unit":unit,


                "canonical_quantity":

                round(grams,2),


                "canonical_unit":"g",


                "conversion_method":

                "density_lookup",


                "confidence_score":0.95

            }


        return {


            "ingredient_name":ingredient_name,

            "quantity":quantity,

            "unit":unit,


            "canonical_quantity":None,


            "canonical_unit":None,


            "conversion_method":"unknown",


            "confidence_score":0.0

        }