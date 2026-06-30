from uuid import uuid4

import pytest
from sqlalchemy import text

from services.database.connection import engine
from services.database.recipe_embedding_loader import RecipeEmbeddingLoader
from services.database.recipe_loader import RecipeLoader
from services.enrichment.recipe_enricher import RecipeEnricher
from services.preprocessing.schema_models import Ingredient, Recipe, RecipeStep


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


def cleanup_recipe(recipe_id):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM recipe_embeddings WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipe_source_tracking WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipe_steps WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipe_ingredients WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )
        conn.execute(
            text("DELETE FROM recipes WHERE recipe_id=:recipe_id"),
            {"recipe_id": recipe_id},
        )


def test_loader_to_vector_search_flow_returns_inserted_recipe():
    require_database_and_pgvector()
    title = f"Vector Search Integration Recipe {uuid4()}"
    source_uuid = uuid4()
    recipe = Recipe(
        title=title,
        description="Temporary vector search integration recipe",
        cuisine="Indian",
        source_type="pytest",
        source_url=f"https://example.com/vector-search-test/{source_uuid}",
        language="english",
        ingredients=[
            Ingredient(ingredient_name="rice", quantity=1, unit="cup"),
            Ingredient(ingredient_name="paneer", quantity=1, unit="cup"),
        ],
        steps=[
            RecipeStep(step_number=1, instruction="Cook rice."),
            RecipeStep(step_number=2, instruction="Add paneer."),
        ],
        metadata={"images": ["https://cdn.example.com/vector.jpg"]},
    )
    recipe = RecipeEnricher().enrich_recipe(recipe)
    embedding = [0.0, 1.0] + [0.0] * 382
    loader = RecipeLoader()
    recipe_id = None

    try:
        recipe_id = loader.insert_recipe(recipe)
        loader.insert_ingredients(recipe_id, recipe.ingredients)
        loader.insert_steps(recipe_id, recipe.steps)
        RecipeEmbeddingLoader(generator=object()).insert_embedding(
            recipe_id,
            embedding,
        )

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT r.recipe_id, r.title
                    FROM recipe_embeddings re
                    JOIN recipes r ON r.recipe_id = re.recipe_id
                    ORDER BY re.embedding <=> CAST(:embedding AS vector)
                    LIMIT 1
                    """
                ),
                {
                    "embedding": "[" + ",".join(str(value) for value in embedding) + "]"
                },
            ).fetchone()

        assert result.recipe_id == recipe_id
        assert result.title == title
    finally:
        if recipe_id is not None:
            cleanup_recipe(recipe_id)
