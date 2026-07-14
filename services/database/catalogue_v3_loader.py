import json
from decimal import Decimal

from sqlalchemy import text

from services.database.catalogue_v3_connection import get_catalogue_v3_engine


ARRAY_FIELDS = {
    "tags",
    "course",
    "diet_tags",
    "allergen_tags",
    "cuisines",
    "meal_types",
    "dish_types",
    "texture",
    "quick_steps",
    "health_tags",
    "efficiency_tags",
    "experience_tags",
    "festival_tags",
}

UPPERCASE_ARRAY_FIELDS = {
    "diet_tags",
    "allergen_tags",
    "health_tags",
    "efficiency_tags",
    "experience_tags",
}

JSON_FIELDS = {
    "nutrition_info",
    "metadata",
    "ingredients_json",
    "prep_steps",
    "cook_steps",
}

COLUMNS = [
    "name",
    "description",
    "nutrition_info",
    "tags",
    "metadata",
    "servings",
    "difficulty_level",
    "youtube_url",
    "image_url",
    "course",
    "region",
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
    "ingredients_json",
    "prep_steps",
    "cook_steps",
    "quick_steps",
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
    "owner_code",
    "owner_name",
    "source",
    "language",
    "is_public",
    "created_by",
    "is_active",
]


class CatalogueV3Loader:
    def __init__(self, engine=None):
        self.engine = engine or get_catalogue_v3_engine()

    def insert_recipe(self, payload: dict) -> str:
        params = self._normalize_payload(payload)
        columns_sql = ", ".join(COLUMNS)
        values_sql = ", ".join(
            self._value_expression(column)
            for column in COLUMNS
        )

        sql = text(
            f"""
            INSERT INTO recipe_catalogue_v3 ({columns_sql})
            VALUES ({values_sql})
            RETURNING recipe_id
            """
        )

        with self.engine.begin() as conn:
            recipe_id = conn.execute(sql, params).scalar_one()

        return str(recipe_id)

    def insert_many(self, payloads: list[dict]) -> list[str]:
        return [
            self.insert_recipe(payload)
            for payload in payloads
        ]

    def _normalize_payload(self, payload):
        payload = dict(payload or {})
        payload.setdefault("nutrition_info", {})
        payload.setdefault("metadata", {})
        payload.setdefault("tags", [])
        payload.setdefault("course", [])
        payload.setdefault("diet_tags", [])
        payload.setdefault("allergen_tags", [])
        payload.setdefault("cuisines", [])
        payload.setdefault("meal_types", [])
        payload.setdefault("dish_types", [])
        payload.setdefault("texture", [])
        payload.setdefault("ingredients_json", [])
        payload.setdefault("prep_steps", [])
        payload.setdefault("cook_steps", [])
        payload.setdefault("quick_steps", [])
        payload.setdefault("popularity_score", 0)
        payload.setdefault("language", "en")
        payload.setdefault("created_by", "system_seed")
        payload.setdefault("is_public", False)
        payload.setdefault("is_active", True)

        if "servings" not in payload:
            raise ValueError("servings is required for recipe_catalogue_v3")

        if "name" not in payload:
            raise ValueError("name is required for recipe_catalogue_v3")

        normalized = {}

        for column in COLUMNS:
            value = payload.get(column)

            if column == "difficulty_level" and value:
                value = str(value).strip().upper()

            if column == "cost_tier" and value:
                value = str(value).strip().upper()

            if column == "diet" and value:
                value = str(value).strip().lower()

            if column in ARRAY_FIELDS:
                value = self._array(value)

                if column in UPPERCASE_ARRAY_FIELDS:
                    value = [
                        item.upper()
                        for item in value
                    ]

            if column in JSON_FIELDS:
                value = self._json(column, value)

            if isinstance(value, Decimal):
                value = float(value)

            normalized[column] = value

        return normalized

    def _array(self, value):
        if value is None:
            return []

        if isinstance(value, str):
            value = [
                item.strip()
                for item in value.split("|")
                if item.strip()
            ]

        if isinstance(value, tuple):
            value = list(value)

        if not isinstance(value, list):
            value = [value]

        cleaned = []

        for item in value:
            text_value = str(item).strip()

            if text_value and text_value not in cleaned:
                cleaned.append(text_value)

        return cleaned

    def _json(self, column, value):
        if value is None:
            value = (
                []
                if column in {"ingredients_json", "prep_steps", "cook_steps"}
                else {}
            )

        return json.dumps(value, default=str)

    def _value_expression(self, column):
        if column in JSON_FIELDS:
            return f"CAST(:{column} AS jsonb)"

        return f":{column}"
