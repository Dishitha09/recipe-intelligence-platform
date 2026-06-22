import re


class IngredientSplitter:

    def split(self, text):

        pattern = r'(?=(?:\d+|\d*[¼½¾⅓⅔⅛⅜⅝⅞]))'

        parts = re.split(pattern, text)

        ingredients = []

        for p in parts:

            p = p.strip()

            if p:

                ingredients.append(p)

        return ingredients