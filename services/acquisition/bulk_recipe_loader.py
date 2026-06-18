from services.database.recipe_loader import RecipeLoader


class BulkRecipeLoader:


    def __init__(self):


        self.loader=RecipeLoader()



    def insert_many(


        self,

        recipes

    ):


        inserted=0


        for recipe in recipes:


            recipe_id=self.loader.insert_recipe(


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


            inserted+=1


        return inserted