import pandas as pd

from services.ingestion.ingredient_ingestion_pipeline import (
    IngredientIngestionPipeline
)


df = pd.read_csv(

    "data/datasets/indian/raw/recipes.csv"

)


recipe = df[df["title"] == "Aloo Gobi Recipe"].iloc[0]


pipeline = IngredientIngestionPipeline()


pipeline.process_recipe(

    recipe_id=82,

    ingredient_text=recipe["ingredients"]

)


print("DONE")