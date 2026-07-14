import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_loader import CatalogueV3Loader


pytestmark = pytest.mark.skipif(
    not os.getenv("CATALOGUE_V3_DATABASE_URL"),
    reason="CATALOGUE_V3_DATABASE_URL is not configured",
)


def test_catalogue_v3_insert_recipe_works():
    loader = CatalogueV3Loader()
    recipe_id = loader.insert_recipe(
        {
            "name": "Pytest Masala Dosa",
            "description": "Crispy dosa with potato masala",
            "servings": 4,
            "difficulty_level": "medium",
            "diet": "Vegetarian",
            "diet_tags": ["vegetarian"],
            "allergen_tags": ["gluten"],
            "cuisines": ["south_indian"],
            "meal_types": ["breakfast"],
            "dish_types": ["dosa"],
            "course": ["main"],
            "ingredients_json": [
                {"name": "dosa batter", "quantity": 3, "unit": "cup"},
                {"name": "potato", "quantity": 4, "unit": "count"},
            ],
            "cook_steps": [
                {"step_number": 1, "instruction": "Spread batter."},
                {"step_number": 2, "instruction": "Cook until crisp."},
            ],
            "source": "pytest",
        }
    )

    with get_catalogue_v3_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT name, servings, difficulty_level, diet, diet_tags
                FROM recipe_catalogue_v3
                WHERE recipe_id = :recipe_id
                """
            ),
            {"recipe_id": recipe_id},
        ).mappings().one()

    assert row["name"] == "Pytest Masala Dosa"
    assert row["servings"] == 4
    assert row["difficulty_level"] == "MEDIUM"
    assert row["diet"] == "vegetarian"
    assert row["diet_tags"] == ["VEGETARIAN"]


def test_catalogue_v3_rejects_invalid_constraints():
    with pytest.raises(IntegrityError):
        with get_catalogue_v3_engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO recipe_catalogue_v3 (
                        name,
                        servings,
                        diet,
                        diet_tags,
                        ingredients_json
                    )
                    VALUES (
                        'X',
                        0,
                        'Vegetarian',
                        ARRAY['vegetarian'],
                        '{}'::jsonb
                    )
                    """
                )
            )
