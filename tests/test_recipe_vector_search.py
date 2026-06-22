from services.retrieval.recipe_vector_search import (

    RecipeVectorSearch

)


searcher = RecipeVectorSearch()


results = searcher.search(

    "South Indian breakfast"

)


for row in results:

    print(row)