from services.rag.recipe_rag import RecipeRAG


rag = RecipeRAG()


response = rag.answer(

    "Suggest South Indian breakfast recipes"

)


print(response)