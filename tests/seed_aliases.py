from sqlalchemy import text

from services.database.connection import engine


aliases = [

("atta","whole_wheat_flour"),

("gehun atta","whole_wheat_flour"),

("gothumai maavu","whole_wheat_flour"),

("kadala","chickpea"),

("kabuli chana","chickpea"),

("besan","gram_flour")

]


with engine.begin() as conn:

    for alias, canonical in aliases:

        conn.execute(

            text("""

            INSERT INTO ingredient_aliases

            (ingredient_id,alias_name)

            SELECT ingredient_id,:alias

            FROM master_ingredients

            WHERE canonical_name=:canonical

            """),

            {

                "alias":alias,

                "canonical":canonical

            }

        )


print("Aliases Seeded")