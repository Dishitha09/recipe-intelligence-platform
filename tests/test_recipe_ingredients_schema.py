from sqlalchemy import text
from services.database.connection import engine

with engine.begin() as conn:

    result = conn.execute(

        text("""

        SELECT

            column_name,

            data_type

        FROM information_schema.columns

        WHERE table_name='recipe_ingredients'

        """)

    )

    for row in result:

        print(row)