from collections import defaultdict


class ShoppingList:


    def generate(self, grocery_dict):


        shopping = []


        for ingredient, values in grocery_dict.items():


            shopping.append(

                {

                    "ingredient": ingredient,

                    "quantity": values["quantity"],

                    "unit": values["unit"]

                }

            )


        shopping = sorted(

            shopping,

            key=lambda x: x["ingredient"]

        )


        return shopping