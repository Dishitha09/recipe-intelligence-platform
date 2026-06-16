from services.ingestion.csv_adapter import CSVAdapter

from services.preprocessing.schema_models import (
    Recipe,
    Ingredient
)

from services.validation.validation_engine import ValidationEngine

from services.database.recipe_loader import RecipeLoader


class RecipePipeline:

    def __init__(self):

        self.validator = ValidationEngine()

        self.loader = RecipeLoader()


    def run_csv_pipeline(self, file_path):


        adapter = CSVAdapter(file_path)

        adapter.extract()

        rows = adapter.transform()


        for row in rows:


            recipe = Recipe(

                title=row["title"],

                cuisine=row["cuisine"],

                description=None,

                source_type="csv",

                source_url=None,

                language="english",

                ingredients=[

                    Ingredient(

                        ingredient_name=row["ingredient"],

                        quantity=100,

                        unit="g"

                    )

                ],

                steps=[]

            )


            result = self.validator.validate(recipe)


            if result["status"] == "ACCEPTED":


                recipe_id = self.loader.insert_recipe(

                    recipe

                )


                self.loader.insert_ingredients(

                    recipe_id,

                    recipe.ingredients

                )


                self.loader.insert_steps(

                    recipe_id,

                    recipe.steps

                )


                print(

                    f"Inserted Recipe ID : {recipe_id}"

                )


            else:


                print(result)