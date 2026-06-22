import pandas as pd

from services.preprocessing.ingredient_cleaner import IngredientCleaner
from services.preprocessing.ingredient_splitter import IngredientSplitter
from services.preprocessing.ingredient_parser import IngredientParser

from services.enrichment.uom.uom_normalizer import UOMNormalizer

from services.database.recipe_loader import RecipeLoader

from services.preprocessing.schema_models import Ingredient


class IngredientIngestionPipeline:


    def __init__(self):

        self.cleaner = IngredientCleaner()

        self.splitter = IngredientSplitter()

        self.parser = IngredientParser()

        self.uom = UOMNormalizer()

        self.loader = RecipeLoader()


    def process_recipe(

        self,

        recipe_id,

        ingredient_text

    ):


        cleaned = self.cleaner.clean(

            ingredient_text

        )


        ingredient_strings = self.splitter.split(

            cleaned

        )


        parsed_ingredients = []


        for item in ingredient_strings:


            ingredient = self.parser.parse(

                item

            )


            parsed_ingredients.append(

                ingredient

            )


        self.loader.insert_ingredients(

            recipe_id,

            parsed_ingredients,

            self.uom

        )


        return parsed_ingredients