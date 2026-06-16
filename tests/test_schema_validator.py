from services.preprocessing.schema_validator import validate_recipe


sample_recipe = {

    "title": "Masala Dosa",

    "description": "Classic South Indian breakfast",

    "cuisine": "South Indian",

    "ingredients": [

        {

            "ingredient_name": "Rice",

            "quantity": 2,

            "unit": "cup"

        }

    ],

    "source_type": "csv"

}


valid, result = validate_recipe(sample_recipe)


print(valid)

print(result)