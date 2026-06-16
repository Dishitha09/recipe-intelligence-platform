from services.grocery.grocery_aggregator import GroceryAggregator

from services.preprocessing.schema_models import (

Recipe,

Ingredient

)



recipe1=Recipe(

title="Masala Dosa",

description="",

cuisine="South Indian",

source_type="csv",

language="english",

ingredients=[

Ingredient(

ingredient_name="Rice",

quantity=400,

unit="g"

),

Ingredient(

ingredient_name="Urad Dal",

quantity=100,

unit="g"

)

]

)



recipe2=Recipe(

title="Paneer Butter Masala",

description="",

cuisine="Indian",

source_type="csv",

language="english",

ingredients=[

Ingredient(

ingredient_name="Paneer",

quantity=250,

unit="g"

),

Ingredient(

ingredient_name="Butter",

quantity=50,

unit="g"

)

]

)



agg=GroceryAggregator()


result=agg.aggregate(

[recipe1,recipe2]

)



print(result)