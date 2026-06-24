import json
import os
from datetime import datetime, timezone

from services.enrichment.uom.ingredient_type import is_liquid
from services.validation.severity import Severity
from services.validation.validation_result import (
    ValidationReport,
    ValidationResult,
)


class ValidationEngine:
    def __init__(self, config_path="configs/validation_checks.json"):
        self.config_path = config_path
        self.check_config = self._load_config(config_path)
        self.checks = [
            ("V01", "Schema Completeness", Severity.CRITICAL, "REJECT", self._v01_schema_completeness),
            ("V02", "Ingredient Count Bounds", Severity.CRITICAL, "REJECT", self._v02_ingredient_count_bounds),
            ("V03", "Step Count Minimum", Severity.CRITICAL, "REJECT", self._v03_step_count_minimum),
            ("V04", "Quantity Sanity", Severity.HIGH, "REVIEW", self._v04_quantity_sanity),
            ("V05", "Allergen Consistency", Severity.HIGH, "REVIEW", self._v05_allergen_consistency),
            ("V06", "UOM Conflict", Severity.HIGH, "REVIEW", self._v06_uom_conflict),
            ("V07", "Nutrition Plausibility", Severity.MEDIUM, "FLAG", self._v07_nutrition_plausibility),
            ("V08", "Enrichment Score", Severity.MEDIUM, "FLAG", self._v08_enrichment_score),
            ("V09", "Duplicate Guard", Severity.CRITICAL, "REJECT", self._v09_duplicate_guard),
            ("V10", "Language Consistency", Severity.MEDIUM, "FLAG", self._v10_language_consistency),
            ("V11", "Image Availability", Severity.LOW, "WARN", self._v11_image_availability),
        ]

    def validate(self, recipe):
        results = []

        for check_id, check_name, severity, action, check in self.checks:
            if not self._is_enabled(check_id):
                continue

            passed, message, details = check(recipe)
            results.append(
                ValidationResult(
                    check_id=check_id,
                    check_name=check_name,
                    passed=passed,
                    severity=severity,
                    action=action,
                    message=message,
                    details=details,
                )
            )

        status = self._verdict(results)
        flags = [
            result.check_id
            for result in results
            if not result.passed and result.severity in {Severity.MEDIUM, Severity.LOW}
        ]

        return ValidationReport(
            status=status,
            check_results=results,
            flags=flags,
            summary={
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "total_checks": len(results),
                "failed_checks": len(
                    [result for result in results if not result.passed]
                ),
                "critical_failures": len(
                    [
                        result
                        for result in results
                        if not result.passed and result.severity == Severity.CRITICAL
                    ]
                ),
                "high_failures": len(
                    [
                        result
                        for result in results
                        if not result.passed and result.severity == Severity.HIGH
                    ]
                ),
                "medium_failures": len(
                    [
                        result
                        for result in results
                        if not result.passed and result.severity == Severity.MEDIUM
                    ]
                ),
            },
        )

    def dead_letter_payload(self, recipe, report):
        return {
            "verdict": report.status,
            "recipe_snapshot": recipe.model_dump()
            if hasattr(recipe, "model_dump")
            else dict(recipe),
            "check_results": [
                result.model_dump()
                for result in report.check_results
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _load_config(self, config_path):
        if not config_path or not os.path.exists(config_path):
            return {}

        with open(config_path, "r", encoding="utf-8") as file:
            if config_path.endswith((".yaml", ".yml")):
                try:
                    import yaml
                except ImportError as exc:
                    raise RuntimeError(
                        "pyyaml is required to load YAML validation config"
                    ) from exc

                return yaml.safe_load(file) or {}

            return json.load(file)

    def _is_enabled(self, check_id):
        return self.check_config.get("checks", {}).get(
            check_id,
            {"enabled": True},
        ).get("enabled", True)

    def _verdict(self, results):
        critical_failures = [
            result
            for result in results
            if not result.passed and result.severity == Severity.CRITICAL
        ]

        if critical_failures:
            return "REJECTED"

        high_failures = [
            result
            for result in results
            if not result.passed and result.severity == Severity.HIGH
        ]
        medium_failures = [
            result
            for result in results
            if not result.passed and result.severity == Severity.MEDIUM
        ]

        if high_failures or len(medium_failures) > 2:
            return "REVIEW"

        return "ACCEPTED"

    def _v01_schema_completeness(self, recipe):
        ingredients = recipe.ingredients or []
        steps = recipe.steps or []
        passed = (
            bool(recipe.title and len(recipe.title.strip()) > 2)
            and len(ingredients) >= 1
            and len(steps) >= 1
        )

        return (
            passed,
            "Schema completeness OK" if passed else "Missing title, ingredients, or steps",
            {
                "title_present": bool(recipe.title),
                "ingredient_count": len(ingredients),
                "step_count": len(steps),
            },
        )

    def _v02_ingredient_count_bounds(self, recipe):
        count = len(recipe.ingredients or [])
        passed = 2 <= count <= 100

        return (
            passed,
            "Ingredient count in bounds" if passed else "Ingredient count outside 2-100",
            {"ingredient_count": count},
        )

    def _v03_step_count_minimum(self, recipe):
        steps = recipe.steps or []
        empty_steps = [
            step.step_number
            for step in steps
            if not step.instruction or not step.instruction.strip()
        ]
        passed = len(steps) >= 1 and not empty_steps

        return (
            passed,
            "Step count OK" if passed else "Recipe has no usable cooking steps",
            {"step_count": len(steps), "empty_steps": empty_steps},
        )

    def _v04_quantity_sanity(self, recipe):
        failures = []

        for ingredient in recipe.ingredients or []:
            quantity = ingredient.canonical_quantity

            if quantity is None:
                quantity = ingredient.quantity

            if quantity is None:
                continue

            if quantity <= 0 or quantity >= 10000:
                failures.append(
                    {
                        "ingredient_name": ingredient.ingredient_name,
                        "quantity": quantity,
                    }
                )

        passed = not failures

        return (
            passed,
            "Quantity sanity OK" if passed else "Quantity outside safe bounds",
            {"failures": failures},
        )

    def _v05_allergen_consistency(self, recipe):
        metadata = recipe.metadata or {}
        claims = {
            claim.lower()
            for claim in metadata.get("dietary_claims", [])
        }
        recipe_allergens = {
            allergen.lower()
            for allergen in metadata.get("allergens", [])
        }
        ingredient_allergens = set()
        nut_ingredients = []

        for ingredient in recipe.ingredients or []:
            ingredient_allergens.update(
                allergen.lower()
                for allergen in ingredient.allergen_flags
            )
            names = {
                str(ingredient.ingredient_name or "").lower(),
                str(ingredient.canonical_name or "").lower(),
            }

            if names & {"cashew", "cashews", "almond", "almonds", "peanut", "peanuts"}:
                nut_ingredients.append(ingredient.ingredient_name)

        missing_allergens = sorted(recipe_allergens - ingredient_allergens)
        nut_free_conflict = "nut-free" in claims and bool(nut_ingredients)
        passed = not missing_allergens and not nut_free_conflict

        return (
            passed,
            "Allergen consistency OK" if passed else "Allergen inconsistency detected",
            {
                "missing_allergens": missing_allergens,
                "nut_free_conflict": nut_free_conflict,
                "nut_ingredients": nut_ingredients,
            },
        )

    def _v06_uom_conflict(self, recipe):
        conflicts = []

        for ingredient in recipe.ingredients or []:
            canonical_name = ingredient.canonical_name or ingredient.ingredient_name

            if (
                ingredient.canonical_unit == "ml"
                and not is_liquid(canonical_name)
                and ingredient.conversion_method != "density_lookup"
            ):
                conflicts.append(
                    {
                        "ingredient_name": ingredient.ingredient_name,
                        "canonical_name": ingredient.canonical_name,
                        "canonical_unit": ingredient.canonical_unit,
                        "conversion_method": ingredient.conversion_method,
                    }
                )

            if "uom_conflict" in ingredient.enrichment_flags:
                conflicts.append(
                    {
                        "ingredient_name": ingredient.ingredient_name,
                        "flag": "uom_conflict",
                    }
                )

        passed = not conflicts

        return (
            passed,
            "UOM conflict check OK" if passed else "UOM conflict detected",
            {"conflicts": conflicts},
        )

    def _v07_nutrition_plausibility(self, recipe):
        nutrition = (recipe.metadata or {}).get("nutrition") or {}
        kcal = nutrition.get("kcal_per_serving")

        if kcal is None:
            return True, "Nutrition unavailable; skipped", {}

        passed = 50 <= kcal <= 2500

        return (
            passed,
            "Nutrition plausible" if passed else "Nutrition implausible",
            {"kcal_per_serving": kcal},
        )

    def _v08_enrichment_score(self, recipe):
        confidence_values = []
        low_confidence = []

        for ingredient in recipe.ingredients or []:
            for field in ["resolution_confidence", "uom_confidence_score"]:
                value = getattr(ingredient, field)

                if value is not None:
                    confidence_values.append(value)

                    if value < 0.70:
                        low_confidence.append(
                            {
                                "ingredient_name": ingredient.ingredient_name,
                                "field": field,
                                "value": value,
                            }
                        )

            if "unresolved_ingredient" in ingredient.enrichment_flags:
                low_confidence.append(
                    {
                        "ingredient_name": ingredient.ingredient_name,
                        "field": "resolution",
                        "value": 0.0,
                    }
                )

        if not confidence_values and not low_confidence:
            return False, "No enrichment confidence available", {}

        average = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )
        passed = average >= 0.70 and not low_confidence

        return (
            passed,
            "Enrichment score OK" if passed else "Low enrichment confidence",
            {
                "average_confidence": round(average, 4),
                "low_confidence": low_confidence,
            },
        )

    def _v09_duplicate_guard(self, recipe):
        duplicate_score = recipe.duplicate_score or 0.0
        passed = recipe.canonical_recipe_id is None and duplicate_score < 0.95

        return (
            passed,
            "Duplicate guard OK" if passed else "Duplicate recipe detected",
            {
                "canonical_recipe_id": recipe.canonical_recipe_id,
                "duplicate_score": duplicate_score,
            },
        )

    def _v10_language_consistency(self, recipe):
        language = (recipe.language or "english").lower()
        passed = language in {"english", "en"}

        return (
            passed,
            "Language consistency OK" if passed else "Non-English content requires translation",
            {"language": recipe.language},
        )

    def _v11_image_availability(self, recipe):
        images = (recipe.metadata or {}).get("images") or []
        passed = len(images) >= 1

        return (
            passed,
            "Image availability OK" if passed else "No image available",
            {"image_count": len(images)},
        )
