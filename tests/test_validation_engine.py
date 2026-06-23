from services.models.recipe import Recipe

from services.models.recipe import Ingredient

from services.validation.validation_engine import (

    ValidationEngine

)


recipe = Recipe(

    title="Masala Dosa",

    description="South Indian breakfast",

    cuisine="South Indian",

    source_type="web",

    source_url="https://example.com",

    language="english",


    ingredients=[

        Ingredient(

            ingredient_name="rice",

            quantity=2,

            unit="cup"

        )

    ]

)


engine = ValidationEngine()


results = engine.validate(recipe)


for r in results:

    print(r)