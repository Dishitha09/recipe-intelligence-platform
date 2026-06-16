from services.validation.rules import *



class ValidationEngine:


    def validate(self, recipe):


        errors=[]


        if not check_title(recipe):

            errors.append("Missing Title")


        if not check_ingredients(recipe):

            errors.append("No Ingredients")


        if not check_source(recipe):

            errors.append("Missing Source Type")



        for ing in recipe.ingredients:


            if not check_positive_quantity(ing):

                errors.append(

                    f"Invalid Quantity : {ing.ingredient_name}"

                )



            if ing.unit:


                if not check_unit(ing.unit):


                    errors.append(

                        f"Invalid Unit : {ing.unit}"

                    )



            if not check_ingredient_name(


                ing.ingredient_name


            ):


                errors.append(


                    "Ingredient Name Missing"


                )




        if len(errors)==0:


            return {

                "status":"ACCEPTED",

                "errors":[]

            }




        return {


            "status":"REVIEW",


            "errors":errors


        }