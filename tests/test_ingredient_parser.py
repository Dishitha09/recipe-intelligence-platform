from services.preprocessing.ingredient_parser import IngredientParser


parser = IngredientParser()


ingredients = [

    "1½ cup potatoes",

    "2 cups cauliflower florets",

    "1 tbsp oil",

    "½ tsp turmeric powder"

]


for i in ingredients:

    result = parser.parse(i)

    print(result)