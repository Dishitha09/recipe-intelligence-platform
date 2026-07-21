import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


SCHEMA_PATH = PROJECT_ROOT / "db" / "catalogue_v3" / "03_operational_tables.sql"


def apply_catalogue_v3_operational_schema():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_catalogue_v3_engine().begin() as conn:
        conn.execute(text(sql))

    return {
        "database": "recipe_catalogue_v3",
        "schema_path": str(SCHEMA_PATH),
        "status": "applied",
    }


def main():
    print(apply_catalogue_v3_operational_schema())


if __name__ == "__main__":
    main()
