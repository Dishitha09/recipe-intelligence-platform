import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.database.catalogue_v3_connection import get_catalogue_v3_engine
from services.database.catalogue_v3_loader import CatalogueV3Loader


def main():
    loader = CatalogueV3Loader()
    recipe_id = loader.insert_recipe(
        {
            "name": "Masala Dosa",
            "description": "Crispy dosa with potato masala",
            "servings": 4,
            "difficulty_level": "MEDIUM",
            "diet": "vegetarian",
            "diet_tags": ["VEGETARIAN"],
            "allergen_tags": ["GLUTEN"],
            "cuisines": ["south_indian"],
            "meal_types": ["breakfast", "dinner"],
            "dish_types": ["dosa"],
            "course": ["main"],
            "ingredients_json": [
                {
                    "name": "dosa batter",
                    "quantity": 3,
                    "unit": "cup",
                },
                {
                    "name": "potato",
                    "quantity": 4,
                    "unit": "count",
                },
                {
                    "name": "mustard seeds",
                    "quantity": 1,
                    "unit": "tsp",
                },
            ],
            "cook_steps": [
                {
                    "step_number": 1,
                    "instruction": "Spread dosa batter on a hot tawa.",
                },
                {
                    "step_number": 2,
                    "instruction": "Cook potato masala with mustard seeds.",
                },
                {
                    "step_number": 3,
                    "instruction": "Fill dosa with masala and serve hot.",
                },
            ],
            "quick_steps": [
                "Spread batter.",
                "Cook potato masala.",
                "Fill and serve.",
            ],
            "source": "manual_test",
            "language": "en",
        }
    )

    print(f"inserted recipe_id={recipe_id}")

    with get_catalogue_v3_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT name, servings, diet, created_at
                FROM recipe_catalogue_v3
                WHERE recipe_id = :recipe_id
                """
            ),
            {"recipe_id": recipe_id},
        ).mappings().one()

    print(
        "loaded "
        f"name={row['name']} "
        f"servings={row['servings']} "
        f"diet={row['diet']} "
        f"created_at={row['created_at']}"
    )


if __name__ == "__main__":
    main()
