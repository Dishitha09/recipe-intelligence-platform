from services.rag.recipe_retriever import RecipeRetriever



retriever=RecipeRetriever()



results=retriever.retrieve(

"South Indian Breakfast"

)



for row in results:

    print(row)