from services.acquisition.recipe_normalizer import (

    RecipeNormalizer

)


row = {

"title":"Masala Dosa",

"cuisine":"South Indian",

"ingredients":"Rice,Urad Dal"

}


normalizer = RecipeNormalizer()


recipe = normalizer.normalize(

    row

)


print(recipe)