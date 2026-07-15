import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "db" / "catalogue_v3" / "01_create_recipe_catalogue_v3.sql"
DATABASE_NAME = "recipe_catalogue_v3"
DEFAULT_ADMIN_URL = "postgresql+psycopg2://admin:admin@localhost:5432/postgres"


def main():
    sys.path.insert(0, str(PROJECT_ROOT))
    load_dotenv(PROJECT_ROOT / ".env")

    admin_url = (
        os.getenv("POSTGRES_ADMIN_URL")
        or _admin_url_from_database_url()
        or DEFAULT_ADMIN_URL
    )
    target_url = _target_url(admin_url)

    create_database_if_missing(admin_url)
    run_schema(target_url)

    print(f"Initialized {DATABASE_NAME}")


def create_database_if_missing(admin_url):
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
            {"database_name": DATABASE_NAME},
        ).scalar()

        if not exists:
            conn.execute(
                text(f'CREATE DATABASE "{DATABASE_NAME}"')
            )


def run_schema(target_url):
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    target_engine = create_engine(target_url)

    with target_engine.begin() as conn:
        conn.exec_driver_sql(schema_sql)


def _target_url(admin_url):
    url = make_url(admin_url)
    return url.set(database=DATABASE_NAME).render_as_string(
        hide_password=False,
    )


def _admin_url_from_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return None

    return make_url(database_url).set(database="postgres").render_as_string(
        hide_password=False,
    )


if __name__ == "__main__":
    main()
