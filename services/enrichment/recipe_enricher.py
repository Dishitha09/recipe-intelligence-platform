from services.enrichment.ingredient_resolution.ingredient_resolver import (
    IngredientResolver,
)
from services.enrichment.state.state_classifier import RecipeStateClassifier
from services.enrichment.uom.uom_normalizer import UOMNormalizer
from services.preprocessing.schema_models import Ingredient


class RecipeEnricher:
    def __init__(
        self,
        ingredient_resolver=None,
        uom_normalizer=None,
        ingredient_repository=None,
        state_classifier=None,
    ):
        self.ingredient_resolver = ingredient_resolver or IngredientResolver()
        self.uom_normalizer = uom_normalizer or UOMNormalizer()
        self.ingredient_repository = ingredient_repository
        self.state_classifier = state_classifier or RecipeStateClassifier()

    def enrich_recipe(self, recipe):
        enriched_ingredients = [
            self.enrich_ingredient(ingredient)
            for ingredient in recipe.ingredients
        ]
        metadata = dict(recipe.metadata or {})
        metadata["enrichment"] = self._summary(enriched_ingredients)
        state_classification = self.state_classifier.classify(recipe)
        metadata["state_classification"] = {
            "state": state_classification.state,
            "region": state_classification.region,
            "confidence": state_classification.confidence,
            "method": state_classification.method,
            "matched_terms": list(state_classification.matched_terms),
        }

        return recipe.model_copy(
            update={
                "ingredients": enriched_ingredients,
                "metadata": metadata,
                "state": recipe.state or state_classification.state,
                "region": recipe.region or state_classification.region,
                "state_confidence": state_classification.confidence,
                "state_method": state_classification.method,
            }
        )

    def enrich_ingredient(self, ingredient):
        resolution = self.ingredient_resolver.resolve(
            ingredient.ingredient_name
        )
        canonical_name = resolution.get("canonical_name")
        uom_name = canonical_name or ingredient.ingredient_name
        normalized = self.uom_normalizer.normalize(
            ingredient_name=uom_name,
            quantity_str=ingredient.quantity,
            unit_str=ingredient.unit,
        )
        flags = self._merge_flags(
            ingredient.enrichment_flags,
            resolution.get("enrichment_flags", []),
            normalized.get("enrichment_flags", []),
        )

        return Ingredient(
            **{
                **ingredient.model_dump(),
                "canonical_name": canonical_name,
                "master_ingredient_id": resolution.get(
                    "master_ingredient_id"
                ) or self._ingredient_id(canonical_name),
                "resolution_method": resolution.get("method"),
                "resolution_tier": resolution.get("tier"),
                "resolution_confidence": resolution.get("confidence_score"),
                "canonical_quantity": normalized.get("canonical_quantity"),
                "canonical_unit": normalized.get("canonical_unit"),
                "conversion_method": normalized.get("conversion_method"),
                "conversion_factor": normalized.get("conversion_factor"),
                "uom_confidence_score": normalized.get("confidence_score"),
                "enrichment_flags": flags,
            }
        )

    def _ingredient_id(self, canonical_name):
        if canonical_name is None or self.ingredient_repository is None:
            return None

        try:
            return self.ingredient_repository.get_ingredient_id(
                canonical_name
            )
        except Exception:
            return None

    def _summary(self, ingredients):
        if not ingredients:
            return {
                "ingredient_resolution_rate": 0.0,
                "uom_resolution_rate": 0.0,
                "enrichment_confidence": 0.0,
            }

        resolved = [
            ingredient
            for ingredient in ingredients
            if ingredient.canonical_name is not None
        ]
        uom_resolved = [
            ingredient
            for ingredient in ingredients
            if ingredient.canonical_unit is not None
        ]
        confidence_values = []

        for ingredient in ingredients:
            if ingredient.resolution_confidence is not None:
                confidence_values.append(ingredient.resolution_confidence)

            if ingredient.uom_confidence_score is not None:
                confidence_values.append(ingredient.uom_confidence_score)

        return {
            "ingredient_resolution_rate": round(
                len(resolved) / len(ingredients),
                4,
            ),
            "uom_resolution_rate": round(
                len(uom_resolved) / len(ingredients),
                4,
            ),
            "enrichment_confidence": round(
                sum(confidence_values) / len(confidence_values),
                4,
            )
            if confidence_values
            else 0.0,
        }

    def _merge_flags(self, *flag_groups):
        flags = []

        for group in flag_groups:
            for flag in group or []:
                if flag not in flags:
                    flags.append(flag)

        return flags
