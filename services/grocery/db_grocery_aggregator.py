from collections import defaultdict

from sqlalchemy import text

from services.database.connection import engine


class DBGroceryAggregator:


    def aggregate(self, recipe_ids):


        grocery = defaultdict(

            lambda: {

                "quantity": 0,

                "unit": ""

            }

        )


        with engine.begin() as conn:


            result = conn.execute(

                text("""

                SELECT

                    mi.canonical_name,

                    ri.quantity,

                    ri.unit


                FROM recipe_ingredients ri


                JOIN master_ingredients mi


                ON ri.ingredient_id = mi.ingredient_id


                WHERE

                ri.recipe_id = ANY(:recipe_ids)

                """),

                {

                    "recipe_ids": recipe_ids

                }

            )


            for row in result:


                ingredient_name = row[0]

                quantity = row[1]

                unit = row[2]


                grocery[ingredient_name]["quantity"] += quantity

                grocery[ingredient_name]["unit"] = unit


        return dict(grocery)