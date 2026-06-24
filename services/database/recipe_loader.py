import json

from sqlalchemy import text

from services.database.connection import engine
from services.database.ingredient_repository import IngredientRepository
from services.enrichment.ingredient_resolution.ingredient_resolver import IngredientResolver
from services.enrichment.uom.uom_normalizer import UOMNormalizer


class RecipeLoader:

    def __init__(self):

        self.repo = IngredientRepository()

        self.resolver = None


    def insert_recipe(self, recipe):

        with engine.begin() as conn:

            result = conn.execute(

                text("""

                INSERT INTO recipes

                (

                title,

                description,

                cuisine,

                source_type,

                source_url,

                language

                )

                VALUES

                (

                :title,

                :description,

                :cuisine,

                :source_type,

                :source_url,

                :language

                )

                RETURNING recipe_id

                """),

                {

                    "title": recipe.title,

                    "description": recipe.description,

                    "cuisine": recipe.cuisine,

                    "source_type": recipe.source_type,

                    "source_url": recipe.source_url,

                    "language": recipe.language

                }

            )

            recipe_id = result.scalar()

            return recipe_id


    def insert_ingredients(

        self,

        recipe_id,

        ingredients,

        uom_normalizer=None

    ):

        uom_normalizer = uom_normalizer or UOMNormalizer()

        with engine.begin() as conn:

            for ing in ingredients:

                canonical_name = ing.canonical_name

                if canonical_name is None:
                    resolved = self._get_resolver().resolve(
                        ing.ingredient_name
                    )
                    canonical_name = resolved["canonical_name"]


                ingredient_id = self.repo.get_ingredient_id(

                    canonical_name

                )


                if ing.canonical_unit is not None:
                    normalized = {
                        "canonical_quantity": ing.canonical_quantity,
                        "canonical_unit": ing.canonical_unit,
                    }
                else:
                    normalized = uom_normalizer.normalize(
                        ingredient_name=canonical_name or ing.ingredient_name,
                        quantity_str=str(ing.quantity),
                        unit_str=ing.unit
                    )


                conn.execute(

                    text("""

                    INSERT INTO recipe_ingredients

                    (

                    recipe_id,

                    ingredient_id,

                    quantity,

                    unit,

                    canonical_quantity,

                    canonical_unit,

                    canonical_name,

                    resolution_method,

                    resolution_tier,

                    resolution_confidence,

                    conversion_method,

                    conversion_factor,

                    uom_confidence_score,

                    enrichment_flags,

                    preparation

                    )

                    VALUES

                    (

                    :recipe_id,

                    :ingredient_id,

                    :quantity,

                    :unit,

                    :canonical_quantity,

                    :canonical_unit,

                    :canonical_name,

                    :resolution_method,

                    :resolution_tier,

                    :resolution_confidence,

                    :conversion_method,

                    :conversion_factor,

                    :uom_confidence_score,

                    CAST(:enrichment_flags AS jsonb),

                    :preparation

                    )

                    """),

                    {

                        "recipe_id": recipe_id,

                        "ingredient_id": ingredient_id,

                        "quantity": ing.quantity,

                        "unit": ing.unit,

                        "canonical_quantity":

                            normalized["canonical_quantity"],

                        "canonical_unit":

                            normalized["canonical_unit"],

                        "canonical_name": canonical_name,

                        "resolution_method": ing.resolution_method,

                        "resolution_tier": ing.resolution_tier,

                        "resolution_confidence": ing.resolution_confidence,

                        "conversion_method": ing.conversion_method,

                        "conversion_factor": ing.conversion_factor,

                        "uom_confidence_score": ing.uom_confidence_score,

                        "enrichment_flags": json.dumps(
                            ing.enrichment_flags
                        ),

                        "preparation":

                            ing.preparation

                    }

                )


                print(

                    canonical_name,

                    "->",

                    normalized["canonical_quantity"],

                    normalized["canonical_unit"]

                )


    def insert_steps(

        self,

        recipe_id,

        steps

    ):


        with engine.begin() as conn:


            for step in steps:


                conn.execute(

                    text("""

                    INSERT INTO recipe_steps

                    (

                    recipe_id,

                    step_number,

                    instruction

                    )

                    VALUES

                    (

                    :recipe_id,

                    :step_number,

                    :instruction

                    )

                    """),

                    {

                        "recipe_id": recipe_id,

                        "step_number": step.step_number,

                        "instruction": step.instruction

                    }

                )

    def _get_resolver(self):
        if self.resolver is None:
            self.resolver = IngredientResolver()

        return self.resolver
