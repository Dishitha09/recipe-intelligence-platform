from services.validation.validation_rules import (

    validate_title,

    validate_source,

    validate_ingredients,

    validate_units

)


class ValidationEngine:


    def validate(

        self,

        recipe

    ):


        results = []


        checks = [

            validate_title,

            validate_source,

            validate_ingredients,

            validate_units

        ]


        for check in checks:


            result = check(recipe)


            results.append(result)


        return results