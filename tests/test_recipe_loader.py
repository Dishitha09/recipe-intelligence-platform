from services.preprocessing.schema_models import (

Recipe,

Ingredient

)

from services.database.recipe_loader import RecipeLoader



recipe=Recipe(

title="Masala Dosa",

description="South Indian Breakfast",

cuisine="South Indian",

source_type="csv",

source_url=None,

language="english",


ingredients=[

Ingredient(

ingredient_name="Rice",

quantity=408,

unit="g"

)

]

)



loader=RecipeLoader()


recipe_id=loader.insert_recipe(

recipe

)



print(recipe_id)