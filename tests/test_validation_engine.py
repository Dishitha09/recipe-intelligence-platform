from services.preprocessing.schema_models import (

    Recipe,

    Ingredient

)

from services.validation.validation_engine import ValidationEngine



recipe = Recipe(

    title="Masala Dosa",

    cuisine="South Indian",

    source_type="csv",

    ingredients=[


        Ingredient(

            ingredient_name="Rice",

            quantity=408,

            unit="g"

        ),



        Ingredient(

            ingredient_name="Oil",

            quantity=15,

            unit="ml"

        )

    ]

)



engine = ValidationEngine()



result = engine.validate(recipe)



print(result)