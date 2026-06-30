import json

from sqlalchemy import text

from services.database.connection import engine
from services.database.fingerprints import recipe_fingerprints
from services.database.ingredient_repository import IngredientRepository
from services.enrichment.ingredient_resolution.ingredient_resolver import IngredientResolver
from services.enrichment.uom.uom_normalizer import UOMNormalizer


class RecipeLoader:

    def __init__(self):

        self.repo = IngredientRepository()

        self.resolver = None


    def insert_recipe(self, recipe):
        fingerprints = recipe_fingerprints(recipe)

        with engine.begin() as conn:
            existing_recipe_id = conn.execute(
                text(
                    """
                    SELECT recipe_id
                    FROM recipes
                    WHERE
                        (:content_hash IS NOT NULL AND content_hash = :content_hash)
                        OR
                        (:source_url_hash IS NOT NULL AND source_url_hash = :source_url_hash)
                    ORDER BY recipe_id
                    LIMIT 1
                    """
                ),
                fingerprints,
            ).scalar()

            params = {
                "title": recipe.title,
                "description": recipe.description,
                "cuisine": recipe.cuisine,
                "state": recipe.state,
                "region": recipe.region,
                "state_confidence": recipe.state_confidence,
                "state_method": recipe.state_method,
                "source_type": recipe.source_type,
                "source_url": recipe.source_url,
                "source_url_hash": fingerprints["source_url_hash"],
                "content_hash": fingerprints["content_hash"],
                "language": recipe.language,
            }

            if existing_recipe_id is not None:
                conn.execute(
                    text(
                        """
                        UPDATE recipes
                        SET
                            title = :title,
                            description = :description,
                            cuisine = :cuisine,
                            state = :state,
                            region = :region,
                            state_confidence = :state_confidence,
                            state_method = :state_method,
                            source_type = :source_type,
                            source_url = :source_url,
                            source_url_hash = :source_url_hash,
                            content_hash = :content_hash,
                            language = :language,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE recipe_id = :recipe_id
                        """
                    ),
                    {**params, "recipe_id": existing_recipe_id},
                )

                return existing_recipe_id

            result = conn.execute(

                text("""

                INSERT INTO recipes

                (

                title,

                description,

                cuisine,

                state,

                region,

                state_confidence,

                state_method,

                source_type,

                source_url,

                source_url_hash,

                content_hash,

                language

                )

                VALUES

                (

                :title,

                :description,

                :cuisine,

                :state,

                :region,

                :state_confidence,

                :state_method,

                :source_type,

                :source_url,

                :source_url_hash,

                :content_hash,

                :language

                )

                RETURNING recipe_id

                """),

                params

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
            conn.execute(
                text(
                    """
                    DELETE FROM recipe_ingredients
                    WHERE recipe_id = :recipe_id
                    """
                ),
                {"recipe_id": recipe_id},
            )

            for ing in ingredients:

                canonical_name = ing.canonical_name

                if (
                    canonical_name is None
                    and ing.resolution_method != "unresolved"
                ):
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


    def insert_steps(

        self,

        recipe_id,

        steps

    ):


        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM recipe_steps
                    WHERE recipe_id = :recipe_id
                    """
                ),
                {"recipe_id": recipe_id},
            )


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

    def record_source(self, recipe_id, recipe, source_name=None, source_type=None, run_id=None):
        fingerprints = recipe_fingerprints(recipe)

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO recipe_source_tracking
                        (
                            run_id,
                            recipe_id,
                            source_name,
                            source_url,
                            source_url_hash,
                            content_hash,
                            source_type
                        )
                    VALUES
                        (
                            :run_id,
                            :recipe_id,
                            :source_name,
                            :source_url,
                            :source_url_hash,
                            :content_hash,
                            :source_type
                        )
                    ON CONFLICT (recipe_id, source_name)
                    WHERE recipe_id IS NOT NULL AND source_name IS NOT NULL
                    DO UPDATE SET
                        run_id = EXCLUDED.run_id,
                        source_url = EXCLUDED.source_url,
                        source_url_hash = EXCLUDED.source_url_hash,
                        content_hash = EXCLUDED.content_hash,
                        source_type = EXCLUDED.source_type,
                        ingested_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "run_id": run_id,
                    "recipe_id": recipe_id,
                    "source_name": source_name,
                    "source_url": recipe.source_url,
                    "source_url_hash": fingerprints["source_url_hash"],
                    "content_hash": fingerprints["content_hash"],
                    "source_type": source_type or recipe.source_type,
                },
            )

    def _get_resolver(self):
        if self.resolver is None:
            self.resolver = IngredientResolver()

        return self.resolver
