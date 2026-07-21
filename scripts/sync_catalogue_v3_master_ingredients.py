import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.connection import engine as operational_engine
from services.database.catalogue_v3_connection import get_catalogue_v3_engine


MASTER_SELECT_SQL = text(
    """
    SELECT ingredient_id, canonical_name, category, default_unit,
           density_g_per_ml, created_at
    FROM master_ingredients
    ORDER BY ingredient_id
    """
)

ALIAS_SELECT_SQL = text(
    """
    SELECT alias_id, ingredient_id, alias_name, language, source
    FROM ingredient_aliases
    ORDER BY alias_id
    """
)

EMBEDDING_SELECT_SQL = text(
    """
    SELECT ingredient_id, embedding::text AS embedding
    FROM ingredient_embeddings
    ORDER BY ingredient_id
    """
)


def sync_catalogue_v3_master_ingredients(include_embeddings=True):
    v3_engine = get_catalogue_v3_engine()

    with operational_engine.connect() as old_conn:
        master_rows = [dict(row) for row in old_conn.execute(MASTER_SELECT_SQL).mappings()]
        alias_rows = [dict(row) for row in old_conn.execute(ALIAS_SELECT_SQL).mappings()]

        try:
            embedding_rows = [
                dict(row)
                for row in old_conn.execute(EMBEDDING_SELECT_SQL).mappings()
            ]
        except Exception:
            embedding_rows = []

    with v3_engine.begin() as conn:
        for row in master_rows:
            conn.execute(
                text(
                    """
                    INSERT INTO master_ingredients (
                        ingredient_id, canonical_name, category, default_unit,
                        density_g_per_ml, created_at
                    )
                    VALUES (
                        :ingredient_id, :canonical_name, :category,
                        :default_unit, :density_g_per_ml, :created_at
                    )
                    ON CONFLICT (ingredient_id)
                    DO UPDATE SET
                        canonical_name = EXCLUDED.canonical_name,
                        category = EXCLUDED.category,
                        default_unit = EXCLUDED.default_unit,
                        density_g_per_ml = EXCLUDED.density_g_per_ml
                    """
                ),
                row,
            )

        for row in alias_rows:
            conn.execute(
                text(
                    """
                    INSERT INTO ingredient_aliases (
                        alias_id, ingredient_id, alias_name, language, source
                    )
                    VALUES (
                        :alias_id, :ingredient_id, :alias_name,
                        :language, :source
                    )
                    ON CONFLICT (alias_id)
                    DO UPDATE SET
                        ingredient_id = EXCLUDED.ingredient_id,
                        alias_name = EXCLUDED.alias_name,
                        language = EXCLUDED.language,
                        source = EXCLUDED.source
                    """
                ),
                row,
            )

        copied_embeddings = 0

        if include_embeddings and embedding_rows and _table_exists(conn, "ingredient_embeddings"):
            for row in embedding_rows:
                conn.execute(
                    text(
                        """
                        INSERT INTO ingredient_embeddings (
                            ingredient_id, embedding
                        )
                        VALUES (
                            :ingredient_id, CAST(:embedding AS vector)
                        )
                        ON CONFLICT (ingredient_id)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            created_at = now()
                        """
                    ),
                    row,
                )
                copied_embeddings += 1

        _reset_sequence(conn, "master_ingredients", "ingredient_id")
        _reset_sequence(conn, "ingredient_aliases", "alias_id")

    return {
        "master_ingredients": len(master_rows),
        "ingredient_aliases": len(alias_rows),
        "ingredient_embeddings": copied_embeddings,
    }


def _table_exists(conn, table_name):
    return bool(
        conn.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": table_name},
        ).scalar()
    )


def _reset_sequence(conn, table_name, id_column):
    sequence_name = conn.execute(
        text("SELECT pg_get_serial_sequence(:table_name, :id_column)"),
        {"table_name": table_name, "id_column": id_column},
    ).scalar()

    if not sequence_name:
        return

    max_id = conn.execute(
        text(f"SELECT COALESCE(MAX({id_column}), 1) FROM {table_name}")
    ).scalar()
    conn.execute(
        text("SELECT setval(:sequence_name, :max_id, true)"),
        {"sequence_name": sequence_name, "max_id": max_id},
    )


def main():
    parser = argparse.ArgumentParser(
        description="Sync master ingredients/aliases from the old operational DB into recipe_catalogue_v3."
    )
    parser.add_argument("--skip-embeddings", action="store_true")
    args = parser.parse_args()

    print(
        sync_catalogue_v3_master_ingredients(
            include_embeddings=not args.skip_embeddings,
        )
    )


if __name__ == "__main__":
    main()
