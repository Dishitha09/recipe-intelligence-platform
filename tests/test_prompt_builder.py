from services.rag.prompt_builder import PromptBuilder


builder = PromptBuilder()


recipes = [

    {

        "title":"Paneer Butter Masala",

        "cuisine":"Indian",

        "similarity":0.93

    },

    {

        "title":"Kadai Paneer",

        "cuisine":"North Indian",

        "similarity":0.87

    }

]


prompt = builder.build(

    "I have paneer and tomatoes",

    recipes

)


print(prompt)