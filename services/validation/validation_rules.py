from services.validation.validation_result import ValidationResult

from services.validation.severity import Severity


VALID_UNITS = {

    "g",

    "kg",

    "mg",

    "cup",

    "cups",

    "tbsp",

    "tsp",

    "bowl",

    "katori",

    "glass",

    "pinch",

    "handful"

}


def validate_title(recipe):

    if not recipe.title:

        return ValidationResult(

            passed=False,

            severity=Severity.CRITICAL,

            message="Title Missing"

        )


    return ValidationResult(

        passed=True,

        severity=Severity.LOW,

        message="OK"

    )




def validate_source(recipe):

    if not recipe.source_url:

        return ValidationResult(

            passed=False,

            severity=Severity.HIGH,

            message="Source Missing"

        )


    return ValidationResult(

        passed=True,

        severity=Severity.LOW,

        message="OK"

    )




def validate_ingredients(recipe):

    if len(recipe.ingredients) == 0:

        return ValidationResult(

            passed=False,

            severity=Severity.CRITICAL,

            message="No Ingredients"

        )


    return ValidationResult(

        passed=True,

        severity=Severity.LOW,

        message="OK"

    )




def validate_units(recipe):


    for ing in recipe.ingredients:


        if ing.unit:


            if ing.unit.lower() not in VALID_UNITS:


                return ValidationResult(

                    passed=False,

                    severity=Severity.HIGH,

                    message=f"Invalid Unit {ing.unit}"

                )


    return ValidationResult(

        passed=True,

        severity=Severity.LOW,

        message="OK"

    )