from services.preprocessing.ingredient_cleaner import IngredientCleaner

cleaner = IngredientCleaner()


text = """
▢ | ½ kg (1.1 lbs.) | bone-in mutton |
(goat or lamb) | ▢ | ¼ | cup | ghee |
"""


print(

    cleaner.clean(text)

)