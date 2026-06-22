from sqlalchemy import text

from services.database.connection import engine


class IngredientRepository:


    def get_ingredient_id(

        self,

        canonical_name

    ):


        with engine.begin() as conn:


            result = conn.execute(

                text("""

                SELECT ingredient_id

                FROM master_ingredients

                WHERE canonical_name=:name

                """),

                {

                    "name": canonical_name

                }

            )


            row = result.fetchone()


            if row:

                return row[0]


            return None