from pathlib import Path
from sqlalchemy import text

from services.database.connection import engine


SCHEMA_DIR = Path("db/schemas")


def run_sql_file(file_path):

    print(f"\nRunning {file_path.name}")

    with open(file_path, "r", encoding="utf-8") as f:

        sql = f.read()

    with engine.begin() as conn:

        conn.execute(text(sql))

    print("Done.")


def initialize_database():

    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))

    for file in sql_files:

        run_sql_file(file)

    print("\nDatabase initialized successfully.")


if __name__ == "__main__":

    initialize_database()