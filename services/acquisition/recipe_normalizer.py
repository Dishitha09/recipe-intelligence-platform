from services.preprocessing.schema_models import (

    Recipe,

    Ingredient,

    RecipeStep

)


class RecipeNormalizer:


    def normalize(self, row):


        title = (

            row.get("title")

            or row.get("RecipeName")

            or row.get("name")

            or "Unknown Recipe"

        )


        cuisine = (

            row.get("cuisine")

            or row.get("Cuisine")

            or "Indian"

        )


        ingredients_text = (

            row.get("ingredients")

            or row.get("Ingredients")

            or row.get("ingredient_list")

            or ""

        )


        ingredients = []


        if isinstance(

            ingredients_text,

            str

        ):


            for item in ingredients_text.split(","):


                ingredients.append(

                    Ingredient(

                        ingredient_name=item.strip()

                    )

                )


        return Recipe(

            title=title,

            description=None,

            cuisine=cuisine,

            state=None,

            region=None,

            ingredients=ingredients,

            steps=[],

            source_type="dataset",

            source_url=None,

            language="english"

        )