from sqlalchemy import text

from services.database.connection import engine


with engine.begin() as conn:


    result = conn.execute(

        text("""

        SELECT extname

        FROM pg_extension

        """)

    )


    for row in result:

        print(row)