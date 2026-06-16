from services.rag.recipe_chat import RecipeChat


chat = RecipeChat()


result = chat.ask(

    "South Indian Breakfast"

)


for r in result:

    print(r)