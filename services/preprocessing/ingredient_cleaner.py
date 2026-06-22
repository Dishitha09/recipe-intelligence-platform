import re


class IngredientCleaner:

    def clean(self, text):

        text = str(text)

        text = text.replace("▢", "")

        text = text.replace("|", " ")

        text = re.sub(r"\([^)]*\)", "", text)

        text = re.sub(r"\s+", " ", text)

        return text.strip()