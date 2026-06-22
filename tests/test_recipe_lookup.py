from sqlalchemy import text

from services.database.connection import engine


with engine.begin() as conn:


    result = conn.execute(

        text("""

        SELECT

        recipe_id,

        title

        FROM recipes

        ORDER BY recipe_id DESC

        LIMIT 5

        """)

    )


    for row in result:

        print(row)