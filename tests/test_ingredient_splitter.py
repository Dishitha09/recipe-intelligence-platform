from services.preprocessing.ingredient_splitter import IngredientSplitter


splitter = IngredientSplitter()


text = "½ kg bone-in mutton ¼ cup ghee"


result = splitter.split(text)


for r in result:

    print(r)