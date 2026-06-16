from services.pipeline.recipe_pipeline import RecipePipeline
from services.preprocessing.schema_models import RecipeStep


steps=[

RecipeStep(

step_number=1,

instruction="Wash rice."

),

RecipeStep(

step_number=2,

instruction="Grind batter."

),

RecipeStep(

step_number=3,

instruction="Cook dosa."

)

]

pipeline=RecipePipeline()


pipeline.run_csv_pipeline(

"sample_recipes.csv"

)