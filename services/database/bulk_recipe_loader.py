import pandas as pd

from services.preprocessing.schema_models import Recipe
from services.database.recipe_loader import RecipeLoader


class BulkRecipeLoader:

    def __init__(self):

        self.loader = RecipeLoader()


    def load_csv(self, csv_path):

        df = pd.read_csv(csv_path)

        inserted = 0


        for _, row in df.iterrows():

            try:

                recipe = Recipe(

                    title=str(row["title"]),

                    description=None,

                    cuisine=None,

                    source_type="web",

                    source_url=row["source_url"],

                    language="english",

                    ingredients=[],

                    steps=[]

                )


                recipe_id = self.loader.insert_recipe(

                    recipe

                )


                inserted += 1


                print(

                    "Inserted:",

                    recipe_id,

                    recipe.title

                )


            except Exception as e:

                print(

                    "Failed:",

                    row["title"],

                    e

                )


        print("\nTotal inserted =", inserted)