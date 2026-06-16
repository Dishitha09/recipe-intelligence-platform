from collections import defaultdict



class GroceryAggregator:


    def aggregate(

        self,

        recipes

    ):


        grocery=defaultdict(float)


        for recipe in recipes:


            for ing in recipe.ingredients:


                grocery[

                    ing.ingredient_name

                ] += ing.quantity



        return dict(grocery)