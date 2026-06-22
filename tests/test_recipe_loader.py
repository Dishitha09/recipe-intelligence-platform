import pandas as pd

from services.preprocessing.schema_models import (
    Recipe,
    Ingredient
)

from services.database.recipe_loader import RecipeLoader


df = pd.read_csv(
    "data/datasets/indian/raw/csv/indian_recipes.csv"
)


loader = RecipeLoader()


for _, row in df.iterrows():

    recipe = Recipe(

        title=row["title"],

        description=None,

        cuisine=row["cuisine"],

        state=row["state"],

        source_type="dataset",

        source_url=None,

        language="english",

        ingredients=[

            Ingredient(

                ingredient_name="Unknown",

                quantity=None,

                unit=None

            )

        ]

    )


    recipe_id = loader.insert_recipe(

        recipe

    )


    print(

        "Inserted:",

        recipe_id,

        recipe.title

    )