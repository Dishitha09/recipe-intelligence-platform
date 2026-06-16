from services.enrichment.uom.ingredient_type import is_liquid

from services.enrichment.uom.density_table import DENSITY_TABLE



UNIT_MAP = {

    "cup":240,

    "cups":240,

    "tbsp":15,

    "tablespoon":15,

    "tsp":5,

    "teaspoon":5,

    "ml":1,

    "liter":1000,

    "litre":1000,

    "l":1000,

    "bowl":250,

    "g":1,

    "gram":1,

    "grams":1,

    "kg":1000

}




def normalize(quantity, unit, ingredient):


    ingredient = ingredient.lower()

    unit = unit.lower()


    if is_liquid(ingredient):


        if unit in UNIT_MAP:

            return (

                quantity * UNIT_MAP[unit],

                "ml"

            )


        return quantity, unit



    if unit in ["g","gram","grams"]:

        return quantity,"g"


    if unit=="kg":

        return quantity*1000,"g"


    if unit in UNIT_MAP:


        ml = quantity*UNIT_MAP[unit]


        density = DENSITY_TABLE.get(

            ingredient,

            1

        )


        grams = ml*density


        return round(grams,2),"g"



    return quantity,unit