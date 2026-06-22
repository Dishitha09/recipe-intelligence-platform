from services.database.bulk_recipe_loader import BulkRecipeLoader


loader = BulkRecipeLoader()


loader.load_csv(

    "data/datasets/indian/raw/recipes.csv"

)