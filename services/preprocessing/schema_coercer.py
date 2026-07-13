import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.ingestion.raw_record import RawRecord
from services.preprocessing.field_mapping import FieldMappingRegistry
from services.preprocessing.ingredient_parser import IngredientParser
from services.preprocessing.schema_models import Ingredient, Recipe, RecipeStep
from services.preprocessing.text_cleaner import clean_text


CANONICAL_FIELDS = [
    "title",
    "original_title",
    "translated_title",
    "description",
    "original_description",
    "translated_description",
    "nutrition_info",
    "tags",
    "servings",
    "difficulty_level",
    "youtube_url",
    "image_url",
    "course",
    "cuisine",
    "state",
    "region",
    "state_confidence",
    "state_method",
    "language",
    "diet",
    "spice_level",
    "complexity",
    "budget_band",
    "diet_tags",
    "allergen_tags",
    "cuisines",
    "meal_types",
    "dish_types",
    "texture",
    "prep_time_min",
    "cook_time_min",
    "total_time_min",
    "passive_time_min",
    "canonical_recipe_id",
    "duplicate_score",
    "estimated_cost_per_serving",
    "popularity_score",
    "side_category",
    "meal_role",
    "dish_family",
    "health_tags",
    "efficiency_tags",
    "experience_tags",
    "cost_tier",
    "festival_tags",
    "ingredients",
    "steps",
    "source_type",
    "source_url",
    "source",
    "owner_code",
    "owner_name",
    "created_by",
    "is_public",
    "is_active",
    "metadata",
]


@dataclass(frozen=True)
class CoercionResult:
    status: str
    record_id: str
    recipe: Optional[Recipe] = None
    dead_letter: Optional[Dict[str, Any]] = None


class SchemaCoercer:
    def __init__(self, mapping_registry):
        self.mapping_registry = mapping_registry
        self.ingredient_parser = IngredientParser()

    @classmethod
    def from_mapping_file(cls, file_path):
        return cls(FieldMappingRegistry.from_file(file_path))

    def coerce(self, raw_record):
        try:
            recipe_data = self.coerce_to_dict(raw_record)
            recipe = Recipe(**recipe_data)

            return CoercionResult(
                status="accepted",
                record_id=raw_record.record_id,
                recipe=recipe,
            )
        except Exception as exc:
            return CoercionResult(
                status="dead_letter",
                record_id=raw_record.record_id,
                dead_letter={
                    "record_id": raw_record.record_id,
                    "source_id": raw_record.source_id,
                    "source_type": raw_record.source_type,
                    "error": str(exc),
                    "record_snapshot": raw_record.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    def coerce_to_dict(self, raw_record):
        if not isinstance(raw_record, RawRecord):
            raise ValueError("SchemaCoercer expects a RawRecord")

        mapping = self.mapping_registry.get(
            raw_record.source_id,
            raw_record.source_type,
        )
        raw_content = dict(raw_record.to_dict()["raw_content"])
        mapped_source_keys = set()

        recipe_data = self._empty_recipe(raw_record)

        for canonical_field, source_fields in mapping.fields.items():
            value, source_key = self._first_present(raw_content, source_fields)

            if source_key is not None:
                mapped_source_keys.add(source_key)

            if value is not None:
                recipe_data[canonical_field] = value

        for key, value in mapping.defaults.items():
            if recipe_data.get(key) is None:
                recipe_data[key] = value

        for field in CANONICAL_FIELDS:
            if recipe_data.get(field) is None and field in raw_content:
                recipe_data[field] = raw_content[field]
                mapped_source_keys.add(field)

        recipe_data["source_type"] = mapping.defaults.get(
            "source_type",
            raw_record.source_type,
        )
        recipe_data["ingredients"] = self._coerce_ingredients(
            recipe_data.get("ingredients"),
            raw_content,
        )
        recipe_data["steps"] = self._coerce_steps(
            recipe_data.get("steps"),
            raw_content,
        )
        recipe_data["metadata"] = {
            "record_id": raw_record.record_id,
            "source_id": raw_record.source_id,
            "source_type": raw_record.source_type,
            "ingested_at": raw_record.ingested_at,
            "source_metadata": raw_record.to_dict()["metadata"],
            "unmapped": {
                key: value
                for key, value in raw_content.items()
                if key not in mapped_source_keys
            },
        }
        images = self._coerce_images(raw_content)

        if images:
            recipe_data["metadata"]["images"] = images

        if images and not recipe_data.get("image_url"):
            recipe_data["image_url"] = images[0]

        return self._canonicalize(recipe_data)

    def to_canonical_json(self, raw_record):
        return json.dumps(
            self.coerce_to_dict(raw_record),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    def _empty_recipe(self, raw_record):
        return {
            field: None
            for field in CANONICAL_FIELDS
        } | {
            "ingredients": [],
            "steps": [],
            "source_type": raw_record.source_type,
        }

    def _first_present(self, raw_content, source_fields):
        for source_field in source_fields:
            if source_field in raw_content:
                value = raw_content[source_field]

                if value != "":
                    return value, source_field

        return None, None

    def _coerce_ingredients(self, value, raw_content):
        ingredient_values = self._as_list(value, split_commas=True)

        if not ingredient_values and raw_content.get("raw_text"):
            ingredient_values = self._extract_section_lines(
                raw_content["raw_text"],
                start_markers=["ingredients:"],
                end_markers=["instructions:", "method:", "steps:"],
            )

        return [
            self._ingredient_to_dict(item)
            for item in ingredient_values
            if str(item).strip()
        ]

    def _ingredient_to_dict(self, item):
        if isinstance(item, dict):
            return {
                "ingredient_name": item.get("ingredient_name")
                or item.get("name")
                or item.get("ingredient"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "preparation": item.get("preparation"),
            }

        parsed = self.ingredient_parser.parse(str(item))

        if not parsed.ingredient_name:
            parsed = Ingredient(
                ingredient_name=str(item).strip(),
                quantity=None,
                unit=None,
                preparation=None,
            )

        return parsed.model_dump()

    def _coerce_steps(self, value, raw_content):
        step_values = self._as_list(value, split_commas=False)

        if not step_values and raw_content.get("raw_text"):
            step_values = self._extract_section_lines(
                raw_content["raw_text"],
                start_markers=["instructions:", "method:", "steps:"],
                end_markers=[],
            )

        steps = []

        for index, step in enumerate(step_values, start=1):
            if isinstance(step, dict):
                instruction = clean_text(
                    step.get("instruction") or step.get("text")
                )
                step_number = step.get("step_number") or index
            else:
                instruction = clean_text(step)
                step_number = index

            if instruction:
                steps.append(
                    RecipeStep(
                        step_number=step_number,
                        instruction=instruction,
                    ).model_dump()
                )

        return steps

    def _as_list(self, value, split_commas=True):
        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        if isinstance(value, str):
            stripped = value.strip()

            if not stripped:
                return []

            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)

                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass

            delimiter_pattern = r"\||\n"

            if split_commas and "|" not in stripped and "\n" not in stripped:
                delimiter_pattern = r"\||,|\n"

            return [
                item.strip()
                for item in re.split(delimiter_pattern, stripped)
                if item.strip()
            ]

        return [value]

    def _extract_section_lines(self, text, start_markers, end_markers):
        lines = [
            line.strip()
            for line in str(text).splitlines()
            if line.strip()
        ]
        selected = []
        collecting = False

        for line in lines:
            normalized_line = line.lower()

            if normalized_line in start_markers:
                collecting = True
                continue

            if collecting and normalized_line in end_markers:
                break

            if collecting:
                selected.append(line)

        return selected

    def _coerce_images(self, raw_content):
        value = (
            raw_content.get("images")
            or raw_content.get("image")
            or raw_content.get("image_url")
            or raw_content.get("photo")
        )

        return self._as_list(value)

    def _canonicalize(self, recipe_data):
        canonical = {
            field: recipe_data.get(field)
            for field in CANONICAL_FIELDS
        }

        for field in [
            "title",
            "original_title",
            "translated_title",
            "description",
            "original_description",
            "translated_description",
            "difficulty_level",
            "youtube_url",
            "image_url",
            "cuisine",
            "state",
            "region",
            "language",
            "diet",
            "spice_level",
            "complexity",
            "budget_band",
            "side_category",
            "meal_role",
            "dish_family",
            "cost_tier",
            "source",
            "source_type",
            "source_url",
            "owner_code",
            "owner_name",
            "created_by",
        ]:
            canonical[field] = clean_text(canonical.get(field))

        for field in [
            "tags",
            "course",
            "diet_tags",
            "allergen_tags",
            "cuisines",
            "meal_types",
            "dish_types",
            "texture",
            "health_tags",
            "efficiency_tags",
            "experience_tags",
            "festival_tags",
        ]:
            canonical[field] = self._as_list(canonical.get(field))

        canonical["nutrition_info"] = canonical.get("nutrition_info") or {}
        canonical["is_public"] = bool(canonical.get("is_public") or False)
        canonical["is_active"] = (
            True if canonical.get("is_active") is None
            else bool(canonical.get("is_active"))
        )

        canonical["ingredients"] = [
            Ingredient(**ingredient).model_dump()
            for ingredient in canonical["ingredients"]
        ]
        canonical["steps"] = [
            RecipeStep(**step).model_dump()
            for step in canonical["steps"]
        ]

        return canonical
