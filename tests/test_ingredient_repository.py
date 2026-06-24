import pytest
from sqlalchemy import text

from services.database.connection import engine
from services.database.ingredient_repository import IngredientRepository


def require_database():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        pytest.skip(f"database unavailable: {exc}")


def test_get_ingredient_id_and_db_alias_resolution():
    require_database()
    repo = IngredientRepository()

    rice_id = repo.get_ingredient_id("rice")
    result = repo.resolve_exact("atta")

    assert rice_id is not None
    assert result["canonical_name"] == "whole_wheat_flour"
    assert result["ingredient_id"] is not None


def test_db_vector_search_returns_seeded_embedding_match():
    require_database()
    repo = IngredientRepository()
    tomato = repo.resolve_exact("tomato")

    if tomato is None:
        pytest.skip("tomato seed ingredient unavailable")

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT embedding
                FROM ingredient_embeddings
                WHERE ingredient_id=:ingredient_id
                """
            ),
            {"ingredient_id": tomato["ingredient_id"]},
        ).fetchone()

    if row is None:
        pytest.skip("ingredient embeddings are not seeded")

    result = repo.search_by_embedding(row[0], threshold=0.99)

    assert result["canonical_name"] == "tomato"
    assert result["confidence_score"] >= 0.99
