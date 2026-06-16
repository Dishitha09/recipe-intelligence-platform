from sqlalchemy import text

from services.database.connection import engine


ingredients = [

    "whole_wheat_flour",

    "chickpea",

    "gram_flour",

    "paneer",

    "rice",

    "onion",

    "tomato"

]


with engine.begin() as conn:

    for item in ingredients:

        conn.execute(

            text("""

            INSERT INTO master_ingredients

            (canonical_name)

            VALUES (:name)

            ON CONFLICT DO NOTHING

            """),

            {"name": item}

        )


print("Master Ingredients Seeded")