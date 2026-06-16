from services.database.ingredient_repository import (

IngredientRepository

)


repo=IngredientRepository()


print(

repo.get_ingredient_id(

"rice"

)

)


print(

repo.get_ingredient_id(

"paneer"

)

)