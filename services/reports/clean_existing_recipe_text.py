from sqlalchemy import text

from services.database.connection import engine
from services.preprocessing.text_cleaner import clean_text


def clean_existing_text():
    counts = {
        "recipes": 0,
        "recipe_steps": 0,
        "recipe_ingredients": 0,
    }

    with engine.begin() as conn:
        recipe_rows = conn.execute(
            text(
                """
                SELECT recipe_id, title, description, cuisine, state, region
                FROM recipes
                """
            )
        ).fetchall()
        for row in recipe_rows:
            conn.execute(
                text(
                    """
                    UPDATE recipes
                    SET
                        title = :title,
                        description = :description,
                        cuisine = :cuisine,
                        state = :state,
                        region = :region
                    WHERE recipe_id = :recipe_id
                    """
                ),
                {
                    "recipe_id": row.recipe_id,
                    "title": clean_text(row.title),
                    "description": clean_text(row.description),
                    "cuisine": clean_text(row.cuisine),
                    "state": clean_text(row.state),
                    "region": clean_text(row.region),
                },
            )
            counts["recipes"] += 1

        step_rows = conn.execute(
            text(
                """
                SELECT recipe_step_id, instruction
                FROM recipe_steps
                """
            )
        ).fetchall()
        for row in step_rows:
            conn.execute(
                text(
                    """
                    UPDATE recipe_steps
                    SET instruction = :instruction
                    WHERE recipe_step_id = :recipe_step_id
                    """
                ),
                {
                    "recipe_step_id": row.recipe_step_id,
                    "instruction": clean_text(row.instruction),
                },
            )
            counts["recipe_steps"] += 1

        ingredient_rows = conn.execute(
            text(
                """
                SELECT recipe_ingredient_id, ingredient_name, preparation
                FROM recipe_ingredients
                """
            )
        ).fetchall()
        for row in ingredient_rows:
            conn.execute(
                text(
                    """
                    UPDATE recipe_ingredients
                    SET
                        ingredient_name = :ingredient_name,
                        preparation = :preparation
                    WHERE recipe_ingredient_id = :recipe_ingredient_id
                    """
                ),
                {
                    "recipe_ingredient_id": row.recipe_ingredient_id,
                    "ingredient_name": clean_text(row.ingredient_name),
                    "preparation": clean_text(row.preparation),
                },
            )
            counts["recipe_ingredients"] += 1

    return counts


def main():
    print(clean_existing_text())


if __name__ == "__main__":
    main()
