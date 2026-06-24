from uuid import uuid4

import pytest
from sqlalchemy import text

from services.database.connection import engine
from services.database.recipe_embedding_loader import RecipeEmbeddingLoader


def require_database_and_pgvector():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
            has_vector = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_extension
                    WHERE extname='vector'
                    """
                )
            ).scalar()
    except Exception as exc:
        pytest.skip(f"database unavailable: {exc}")

    if not has_vector:
        pytest.skip("pgvector extension is not installed")


def insert_recipe():
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO recipes
                    (title, description, cuisine, source_type, source_url, language)
                VALUES
                    (:title, :description, 'Indian', 'pytest', :source_url, 'english')
                RETURNING recipe_id
                """
            ),
            {
                "title": f"Embedding Integration Recipe {uuid4()}",
                "description": "Temporary embedding test recipe",
                "source_url": "https://example.com/embedding-test",
            },
        ).scalar()


def cleanup_recipe(recipe_id):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM recipe_embeddings WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipes WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )


def test_recipe_embedding_loader_inserts_vector_embedding():
    require_database_and_pgvector()
    recipe_id = insert_recipe()
    embedding = [1.0] + [0.0] * 383

    try:
        RecipeEmbeddingLoader(generator=object()).insert_embedding(
            recipe_id,
            embedding,
        )

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT recipe_id
                    FROM recipe_embeddings
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT 1
                    """
                ),
                {
                    "embedding": "[" + ",".join(str(value) for value in embedding) + "]"
                },
            ).fetchone()

        assert row[0] == recipe_id
    finally:
        cleanup_recipe(recipe_id)
