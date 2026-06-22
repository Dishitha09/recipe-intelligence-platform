from services.rag.recipe_rag import RecipeRAG


assistant = RecipeRAG()


response = assistant.answer(

    "Suggest South Indian breakfast recipes"

)


print(response)