import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


VIEW_SQL_PATH = (
    PROJECT_ROOT / "db" / "catalogue_v3" / "02_create_reviewer_format_view.sql"
)


def create_reviewer_view():
    sql = VIEW_SQL_PATH.read_text(encoding="utf-8")

    with get_catalogue_v3_engine().begin() as conn:
        conn.exec_driver_sql(sql)

    return {
        "view": "recipe_catalogue_v3_reviewer_format",
        "sql_path": str(VIEW_SQL_PATH),
    }


def main():
    print(create_reviewer_view())


if __name__ == "__main__":
    main()
