import json

from sqlalchemy import text

from services.database.connection import engine
from services.database.fingerprints import recipe_fingerprints
from services.database.ingredient_repository import IngredientRepository
from services.enrichment.ingredient_resolution.ingredient_resolver import IngredientResolver
from services.enrichment.uom.uom_normalizer import UOMNormalizer
from services.preprocessing.text_cleaner import clean_text
from services.reliability.retry import transient_retry


class RecipeLoader:

    def __init__(self):

        self.repo = IngredientRepository()

        self.resolver = None

    def _array(self, values, uppercase=False, lowercase=False):
        cleaned = []

        for value in values or []:
            text_value = clean_text(value)

            if not text_value:
                continue

            if uppercase:
                text_value = text_value.upper()

            if lowercase:
                text_value = text_value.lower()

            if text_value not in cleaned:
                cleaned.append(text_value)

        return cleaned

    def _json(self, value):
        if value is None:
            value = {}

        return json.dumps(value, default=str)

    def _image_url(self, recipe):
        if recipe.image_url:
            return clean_text(recipe.image_url)

        metadata = recipe.metadata or {}
        images = metadata.get("images") or []

        if images:
            return clean_text(images[0])

        return None

    def _youtube_url(self, recipe):
        if recipe.youtube_url:
            return clean_text(recipe.youtube_url)

        source_url = clean_text(recipe.source_url)

        if source_url and "youtube.com" in source_url:
            return source_url

        if source_url and "youtu.be" in source_url:
            return source_url

        return None

    def _step_json(self, steps):
        return [
            {
                "step_number": step.step_number,
                "instruction": clean_text(step.instruction),
            }
            for step in steps or []
        ]


    @transient_retry
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
                "name": clean_text(recipe.title),
                "title": clean_text(recipe.title),
                "description": clean_text(recipe.description),
                "cuisine": clean_text(recipe.cuisine),
                "state": clean_text(recipe.state),
                "region": clean_text(recipe.region),
                "state_confidence": recipe.state_confidence,
                "state_method": recipe.state_method,
                "source_type": clean_text(recipe.source_type),
                "source_url": clean_text(recipe.source_url),
                "source_url_hash": fingerprints["source_url_hash"],
                "content_hash": fingerprints["content_hash"],
                "language": clean_text(recipe.language) or "en",
                "nutrition_info": self._json(recipe.nutrition_info or {}),
                "tags": self._array(recipe.tags),
                "metadata": self._json(recipe.metadata or {}),
                "servings": recipe.servings or 1,
                "difficulty_level": (
                    clean_text(recipe.difficulty_level).upper()
                    if recipe.difficulty_level
                    else "MEDIUM"
                ),
                "youtube_url": self._youtube_url(recipe),
                "image_url": self._image_url(recipe),
                "course": self._array(recipe.course, lowercase=True),
                "diet": clean_text(recipe.diet).lower()
                if recipe.diet
                else None,
                "spice_level": clean_text(recipe.spice_level),
                "complexity": clean_text(recipe.complexity),
                "budget_band": clean_text(recipe.budget_band),
                "diet_tags": self._array(recipe.diet_tags, uppercase=True),
                "allergen_tags": self._array(
                    recipe.allergen_tags,
                    uppercase=True,
                ),
                "cuisines": self._array(
                    recipe.cuisines or ([recipe.cuisine] if recipe.cuisine else [])
                ),
                "meal_types": self._array(recipe.meal_types, lowercase=True),
                "dish_types": self._array(recipe.dish_types, lowercase=True),
                "texture": self._array(recipe.texture, lowercase=True),
                "prep_time_min": recipe.prep_time_min,
                "cook_time_min": recipe.cook_time_min,
                "total_time_min": recipe.total_time_min
                or (
                    (recipe.prep_time_min or 0) + (recipe.cook_time_min or 0)
                    if recipe.prep_time_min or recipe.cook_time_min
                    else None
                ),
                "passive_time_min": recipe.passive_time_min,
                "ingredients_json": json.dumps(
                    [
                        ingredient.model_dump(mode="json")
                        for ingredient in recipe.ingredients or []
                    ],
                    default=str,
                ),
                "prep_steps": json.dumps([], default=str),
                "cook_steps": json.dumps(self._step_json(recipe.steps), default=str),
                "quick_steps": json.dumps(
                    [
                        clean_text(step.instruction)
                        for step in (recipe.steps or [])[:5]
                    ],
                    default=str,
                ),
                "estimated_cost_per_serving": recipe.estimated_cost_per_serving,
                "popularity_score": recipe.popularity_score or 0,
                "side_category": clean_text(recipe.side_category),
                "meal_role": clean_text(recipe.meal_role),
                "dish_family": clean_text(recipe.dish_family),
                "health_tags": self._array(recipe.health_tags, uppercase=True),
                "efficiency_tags": self._array(
                    recipe.efficiency_tags,
                    uppercase=True,
                ),
                "experience_tags": self._array(
                    recipe.experience_tags,
                    uppercase=True,
                ),
                "cost_tier": clean_text(recipe.cost_tier).upper()
                if recipe.cost_tier
                else None,
                "festival_tags": self._array(
                    recipe.festival_tags,
                    lowercase=True,
                ),
                "owner_code": clean_text(recipe.owner_code),
                "owner_name": clean_text(recipe.owner_name),
                "source": clean_text(recipe.source) or clean_text(recipe.source_type),
                "created_by": clean_text(recipe.created_by),
                "is_public": bool(recipe.is_public),
                "is_active": bool(recipe.is_active),
            }

            if existing_recipe_id is not None:
                conn.execute(
                    text(
                        """
                        UPDATE recipes
                        SET
                            title = :title,
                            name = :name,
                            description = :description,
                            cuisine = :cuisine,
                            state = :state,
                            region = :region,
                            state_confidence = :state_confidence,
                            state_method = :state_method,
                            language = :language,
                            nutrition_info = CAST(:nutrition_info AS jsonb),
                            tags = :tags,
                            metadata = CAST(:metadata AS jsonb),
                            servings = :servings,
                            difficulty_level = :difficulty_level,
                            youtube_url = :youtube_url,
                            image_url = :image_url,
                            course = :course,
                            diet = :diet,
                            spice_level = :spice_level,
                            complexity = :complexity,
                            budget_band = :budget_band,
                            diet_tags = :diet_tags,
                            allergen_tags = :allergen_tags,
                            cuisines = :cuisines,
                            meal_types = :meal_types,
                            dish_types = :dish_types,
                            texture = :texture,
                            prep_time_min = :prep_time_min,
                            cook_time_min = :cook_time_min,
                            total_time_min = :total_time_min,
                            passive_time_min = :passive_time_min,
                            ingredients_json = CAST(:ingredients_json AS jsonb),
                            prep_steps = CAST(:prep_steps AS jsonb),
                            cook_steps = CAST(:cook_steps AS jsonb),
                            quick_steps = CAST(:quick_steps AS jsonb),
                            estimated_cost_per_serving = :estimated_cost_per_serving,
                            popularity_score = :popularity_score,
                            side_category = :side_category,
                            meal_role = :meal_role,
                            dish_family = :dish_family,
                            health_tags = :health_tags,
                            efficiency_tags = :efficiency_tags,
                            experience_tags = :experience_tags,
                            cost_tier = :cost_tier,
                            festival_tags = :festival_tags,
                            owner_code = :owner_code,
                            owner_name = :owner_name,
                            source = :source,
                            created_by = :created_by,
                            is_public = :is_public,
                            is_active = :is_active,
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

                name,

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

                language,

                nutrition_info,

                tags,

                metadata,

                servings,

                difficulty_level,

                youtube_url,

                image_url,

                course,

                diet,

                spice_level,

                complexity,

                budget_band,

                diet_tags,

                allergen_tags,

                cuisines,

                meal_types,

                dish_types,

                texture,

                prep_time_min,

                cook_time_min,

                total_time_min,

                passive_time_min,

                ingredients_json,

                prep_steps,

                cook_steps,

                quick_steps,

                estimated_cost_per_serving,

                popularity_score,

                side_category,

                meal_role,

                dish_family,

                health_tags,

                efficiency_tags,

                experience_tags,

                cost_tier,

                festival_tags,

                owner_code,

                owner_name,

                source,

                created_by,

                is_public,

                is_active

                )

                VALUES

                (

                :title,

                :name,

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

                :language,

                CAST(:nutrition_info AS jsonb),

                :tags,

                CAST(:metadata AS jsonb),

                :servings,

                :difficulty_level,

                :youtube_url,

                :image_url,

                :course,

                :diet,

                :spice_level,

                :complexity,

                :budget_band,

                :diet_tags,

                :allergen_tags,

                :cuisines,

                :meal_types,

                :dish_types,

                :texture,

                :prep_time_min,

                :cook_time_min,

                :total_time_min,

                :passive_time_min,

                CAST(:ingredients_json AS jsonb),

                CAST(:prep_steps AS jsonb),

                CAST(:cook_steps AS jsonb),

                CAST(:quick_steps AS jsonb),

                :estimated_cost_per_serving,

                :popularity_score,

                :side_category,

                :meal_role,

                :dish_family,

                :health_tags,

                :efficiency_tags,

                :experience_tags,

                :cost_tier,

                :festival_tags,

                :owner_code,

                :owner_name,

                :source,

                :created_by,

                :is_public,

                :is_active

                )

                RETURNING recipe_id

                """),

                params

            )

            recipe_id = result.scalar()

            return recipe_id


    @transient_retry
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

                    ingredient_name,

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

                    :ingredient_name,

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

                        "ingredient_name": clean_text(ing.ingredient_name),

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

                            clean_text(ing.preparation)

                    }

                )


    @transient_retry
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

                        "instruction": clean_text(step.instruction)

                    }

                )

    @transient_retry
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
