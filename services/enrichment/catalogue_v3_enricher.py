import re
from dataclasses import dataclass
from typing import Any

from services.enrichment.state.state_classifier import RecipeStateClassifier
from services.enrichment.uom.uom_normalizer import UOMNormalizer
from services.preprocessing.ingredient_parser import IngredientParser


@dataclass(frozen=True)
class CatalogueV3Enrichment:
    updates: dict[str, Any]
    metadata_patch: dict[str, Any]


class CatalogueV3Enricher:
    def __init__(
        self,
        ingredient_parser=None,
        state_classifier=None,
        uom_normalizer=None,
    ):
        self.ingredient_parser = ingredient_parser or IngredientParser()
        self.state_classifier = state_classifier or RecipeStateClassifier()
        self.uom_normalizer = uom_normalizer or UOMNormalizer()

    def enrich_row(self, row: dict[str, Any]) -> CatalogueV3Enrichment:
        ingredients = self._enrich_ingredients(row.get("ingredients_json") or [])
        text = self._row_text(row, ingredients)
        dish_text = self._dish_text(row)
        dish_family = self._dish_family(dish_text)
        dish_types = self._dish_types(dish_text)
        inferred_diet = self._diet(row, text)
        diet_tags = self._diet_tags(inferred_diet, text, row.get("diet_tags") or [])
        allergen_tags = self._allergen_tags(text, row.get("allergen_tags") or [])
        total_time = self._total_time(row)
        difficulty = self._difficulty(row, total_time)
        efficiency_tags = self._efficiency_tags(
            row,
            total_time,
            row.get("efficiency_tags") or [],
        )
        health_tags = self._health_tags(
            text,
            diet_tags,
            allergen_tags,
            row.get("health_tags") or [],
        )
        meal_role = self._meal_role(dish_text, dish_family, row.get("meal_role"))
        cost_tier = self._cost_tier(text, row.get("cost_tier"))
        state_region = self._state_region(row)

        updates = {
            "ingredients_json": ingredients,
            "difficulty_level": row.get("difficulty_level") or difficulty,
            "diet": inferred_diet,
            "diet_tags": diet_tags,
            "allergen_tags": allergen_tags,
            "dish_types": dish_types,
            "dish_family": dish_family,
            "meal_role": meal_role,
            "health_tags": health_tags,
            "efficiency_tags": efficiency_tags,
            "cost_tier": cost_tier,
            "budget_band": row.get("budget_band") or cost_tier,
            "complexity": row.get("complexity") or difficulty,
            "region": row.get("region") or state_region.get("region"),
        }
        clearable_fields = {
            "dish_types",
            "dish_family",
            "meal_role",
        }
        updates = {
            key: value
            for key, value in updates.items()
            if value not in (None, [], {}) or key in clearable_fields
        }

        return CatalogueV3Enrichment(
            updates=updates,
            metadata_patch={
                "catalogue_v3_enrichment": {
                    "method": "deterministic_rule_based",
                    "version": "2026-07-15",
                    "generated_text": False,
                    "inferred_fields": sorted(updates.keys()),
                    "state_classification": state_region,
                }
            },
        )

    def _enrich_ingredients(self, ingredients):
        enriched = []

        for index, item in enumerate(ingredients, start=1):
            ingredient = dict(item or {})
            raw_text = (
                ingredient.get("raw_text")
                or ingredient.get("item")
                or ingredient.get("name")
                or ""
            )
            raw_text = self._clean_text(raw_text)
            parsed = self.ingredient_parser.parse(raw_text)
            name = ingredient.get("name") or ingredient.get("item")
            quantity = ingredient.get("quantity")
            unit = ingredient.get("unit")
            ingredient_name = self._clean_text(name or parsed.ingredient_name)

            ingredient.setdefault("raw_text", raw_text)
            ingredient.setdefault("source_position", index)
            ingredient["raw_text"] = raw_text
            ingredient["name"] = ingredient_name

            if quantity is None:
                quantity = parsed.quantity

            if unit is None:
                unit = parsed.unit

            ingredient["quantity"] = quantity
            ingredient["unit"] = unit

            normalized = self.uom_normalizer.normalize(
                ingredient_name=ingredient_name,
                quantity_str=quantity,
                unit_str=unit,
            )
            ingredient["canonical_quantity"] = normalized.get(
                "canonical_quantity"
            )
            ingredient["canonical_unit"] = normalized.get("canonical_unit")
            ingredient["normalized_text"] = self._ingredient_display_text(
                ingredient_name,
                quantity,
                unit,
            )
            ingredient["conversion_method"] = normalized.get(
                "conversion_method"
            )
            ingredient["conversion_factor"] = normalized.get(
                "conversion_factor"
            )
            ingredient["uom_confidence_score"] = normalized.get(
                "confidence_score"
            )
            ingredient["normalization_flags"] = normalized.get(
                "enrichment_flags",
                [],
            )

            enriched.append(ingredient)

        return enriched

    def _row_text(self, row, ingredients):
        parts = [
            row.get("name"),
            row.get("description"),
            row.get("diet"),
            row.get("region"),
            row.get("course"),
            row.get("cuisines"),
            row.get("meal_types"),
            row.get("tags"),
            row.get("dish_types"),
            [item.get("raw_text") or item.get("name") for item in ingredients],
        ]
        return " ".join(self._flatten(parts)).lower()

    def _dish_text(self, row):
        parts = [
            row.get("name"),
            row.get("course"),
            row.get("cuisines"),
            row.get("meal_types"),
            row.get("tags"),
        ]
        return " ".join(self._flatten(parts)).lower()

    def _flatten(self, values):
        flattened = []

        for value in values:
            if value is None:
                continue
            if isinstance(value, dict):
                flattened.extend(self._flatten(value.values()))
            elif isinstance(value, (list, tuple, set)):
                flattened.extend(self._flatten(value))
            else:
                flattened.append(str(value))

        return flattened

    def _clean_text(self, value):
        text = str(value or "")
        replacements = {
            "\u00c2\u00bc": " 1/4",
            "\u00c2\u00bd": " 1/2",
            "\u00c2\u00be": " 3/4",
            "Ã‚Â¼": " 1/4",
            "Ã‚Â½": " 1/2",
            "Ã‚Â¾": " 3/4",
            "\u00e2\u20ac\u201c": "-",
            "\u00e2\u20ac\u201d": "-",
            "\u00e2\u20ac\u2122": "'",
            "\u00e2\u20ac\u0153": '"',
            "\u00e2\u20ac\u009d": '"',
        }

        for bad_text, replacement in replacements.items():
            text = text.replace(bad_text, replacement)

        return re.sub(r"\s+", " ", text).strip()

    def _ingredient_display_text(self, name, quantity, unit):
        parts = []

        if quantity is not None:
            parts.append(self._format_quantity(quantity))

        if unit:
            parts.append(str(unit).strip())

        if name:
            parts.append(str(name).strip())

        return " ".join(part for part in parts if part).strip()

    def _format_quantity(self, quantity):
        try:
            value = float(quantity)
        except (TypeError, ValueError):
            return str(quantity)

        if value.is_integer():
            return str(int(value))

        return f"{value:g}"

    def _diet(self, row, text):
        existing = row.get("diet")

        if existing:
            return self._canonical_diet(existing)

        if self._contains_any(text, MEAT_TERMS):
            return "non_vegetarian"

        if self._contains_any(text, EGG_TERMS):
            return "egg"

        if (
            "vegan" in text
            and not self._contains_any(text, DAIRY_TERMS | EGG_TERMS | MEAT_TERMS)
        ):
            return "vegan"

        if "vegetarian" in text or "veg " in f"{text} ":
            return "vegetarian"

        return None

    def _diet_tags(self, diet, text, existing):
        tags = [self._tag(tag) for tag in existing or []]

        if diet:
            tags.append(self._tag(diet))

        if self._contains_any(text, EGG_TERMS):
            tags.append("EGG")

        if self._contains_any(text, MEAT_TERMS):
            tags.append("NON_VEGETARIAN")

        return self._dedupe(tags)

    def _canonical_diet(self, value):
        normalized = re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()

        if "non" in normalized and ("vegetarian" in normalized or "vegeterian" in normalized):
            return "non_vegetarian"
        if "egg" in normalized:
            return "egg"
        if "vegan" in normalized:
            return "vegan"
        if "vegetarian" in normalized or "vegeterian" in normalized:
            return "vegetarian"
        if "diabetic" in normalized:
            return "diabetic_friendly"

        return normalized.replace(" ", "_") or None

    def _tag(self, value):
        return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")

    def _allergen_tags(self, text, existing):
        tags = [tag.upper() for tag in existing or []]

        allergen_terms = {
            "DAIRY": DAIRY_TERMS,
            "EGG": EGG_TERMS,
            "GLUTEN": GLUTEN_TERMS,
            "NUTS": NUT_TERMS,
            "SEAFOOD": SEAFOOD_TERMS,
            "SOY": SOY_TERMS,
        }

        for tag, terms in allergen_terms.items():
            if self._contains_any(text, terms):
                tags.append(tag)

        return self._dedupe(tags)

    def _health_tags(self, text, diet_tags, allergen_tags, existing):
        tags = [tag.upper() for tag in existing or []]

        if self._contains_any(text, HIGH_PROTEIN_TERMS):
            tags.append("HIGH_PROTEIN")

        if "VEGAN" in diet_tags:
            tags.append("VEGAN")

        if "GLUTEN" not in allergen_tags and self._contains_any(
            text,
            NATURALLY_GLUTEN_FREE_TERMS,
        ):
            tags.append("GLUTEN_FREE")

        return self._dedupe(tags)

    def _difficulty(self, row, total_time):
        step_count = len(row.get("cook_steps") or [])
        ingredient_count = len(row.get("ingredients_json") or [])

        if total_time is not None:
            if total_time <= 30 and step_count <= 8:
                return "EASY"
            if total_time <= 90 and ingredient_count <= 20:
                return "MEDIUM"
            if total_time <= 180:
                return "HARD"
            return "EXPERT"

        if step_count <= 5 and ingredient_count <= 8:
            return "EASY"
        if step_count <= 12:
            return "MEDIUM"

        return "HARD"

    def _efficiency_tags(self, row, total_time, existing):
        tags = [tag.upper() for tag in existing or []]

        if total_time is not None and total_time <= 30:
            tags.append("QUICK")

        if len(row.get("cook_steps") or []) <= 6:
            tags.append("BEGINNER_FRIENDLY")

        if total_time is not None and total_time >= 90:
            tags.append("MEAL_PREP")

        return self._dedupe(tags)

    def _dish_family(self, text):
        for family, terms in DISH_FAMILY_TERMS.items():
            if self._contains_any(text, terms):
                return family

        return None

    def _dish_types(self, text):
        dish_types = []

        for dish_type, terms in DISH_TYPE_TERMS.items():
            if self._contains_any(text, terms):
                dish_types.append(dish_type)

        return dish_types

    def _meal_role(self, text, dish_family, existing):
        if existing:
            return existing

        if dish_family in {"chutney", "pickle", "raita", "sambar", "dal"}:
            return "condiment" if dish_family in {"chutney", "pickle", "raita"} else "dal_side"

        if dish_family in {"biryani", "pulao", "khichdi", "dosa", "idli"}:
            return "complete_meal"

        if self._contains_any(text, DESSERT_TERMS):
            return "dessert"

        if self._contains_any(text, SNACK_TERMS):
            return "snack_anchor"

        if self._contains_any(text, PROTEIN_TERMS):
            return "protein_side"

        return None

    def _cost_tier(self, text, existing):
        if existing:
            return existing

        if self._contains_any(text, PREMIUM_TERMS):
            return "PREMIUM"

        if self._contains_any(text, BUDGET_TERMS):
            return "BUDGET"

        return "MID_RANGE"

    def _total_time(self, row):
        total_time = row.get("total_time_min")

        if total_time is not None:
            return total_time

        prep_time = row.get("prep_time_min")
        cook_time = row.get("cook_time_min")

        if prep_time is not None and cook_time is not None:
            return prep_time + cook_time

        return None

    def _state_region(self, row):
        recipe = _RecipeProxy(row)
        classification = self.state_classifier.classify(recipe)

        return {
            "state": classification.state,
            "region": classification.region,
            "confidence": classification.confidence,
            "method": classification.method,
            "matched_terms": list(classification.matched_terms),
        }

    def _contains_any(self, text, terms):
        return any(
            re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text)
            for term in terms
        )

    def _merge(self, existing, inferred):
        return self._dedupe([*(existing or []), *(inferred or [])])

    def _dedupe(self, values):
        deduped = []

        for value in values or []:
            if value and value not in deduped:
                deduped.append(value)

        return deduped


class _RecipeProxy:
    def __init__(self, row):
        self.title = row.get("name")
        self.original_title = None
        self.description = row.get("description")
        self.cuisine = " ".join(row.get("cuisines") or [])
        self.state = None
        self.region = row.get("region")
        self.source_url = (row.get("metadata") or {}).get("source_url")
        self.metadata = {
            "tags": row.get("tags") or [],
            "source_metadata": row.get("metadata") or {},
        }


MEAT_TERMS = {
    "chicken",
    "mutton",
    "lamb",
    "fish",
    "prawn",
    "shrimp",
    "beef",
    "pork",
    "meat",
    "keema",
}
SEAFOOD_TERMS = {"fish", "prawn", "shrimp", "crab"}
EGG_TERMS = {"egg", "eggs"}
DAIRY_TERMS = {"milk", "curd", "yogurt", "paneer", "cheese", "cream", "ghee", "butter"}
GLUTEN_TERMS = {"wheat", "atta", "maida", "bread", "pasta", "rava", "sooji", "semolina"}
NUT_TERMS = {"peanut", "cashew", "almond", "pistachio", "walnut"}
SOY_TERMS = {"soy", "soya", "tofu"}
HIGH_PROTEIN_TERMS = MEAT_TERMS | EGG_TERMS | {"paneer", "dal", "lentil", "chickpea", "chana", "rajma", "tofu", "soy", "sprouts"}
NATURALLY_GLUTEN_FREE_TERMS = {"rice", "poha", "ragi", "jowar", "bajra", "sabudana"}
PROTEIN_TERMS = MEAT_TERMS | EGG_TERMS | {"paneer", "dal", "chana", "rajma"}
PREMIUM_TERMS = {"saffron", "mutton", "lamb", "prawn", "shrimp", "cashew", "almond", "pistachio"}
BUDGET_TERMS = {"rice", "poha", "dal", "potato", "onion", "chana", "atta", "oats"}
DESSERT_TERMS = {
    "barfi",
    "burfi",
    "halwa",
    "kalakand",
    "kheer",
    "laddu",
    "ladoo",
    "payasam",
    "rabdi",
    "rasgulla",
    "rasmalai",
    "shahi tukda",
}
SNACK_TERMS = {"chaat", "pakora", "kabab", "kebab", "cutlet", "samosa", "vada", "bhaji", "sandwich"}

DISH_FAMILY_TERMS = {
    "biryani": {"biryani"},
    "pulao": {"pulao", "pulav"},
    "dosa": {"dosa"},
    "idli": {"idli"},
    "chutney": {"chutney"},
    "sambar": {"sambar"},
    "dal": {"dal", "lentil"},
    "curry": {"curry", "gravy"},
    "kabab": {"kabab", "kebab"},
    "kheer": {"kheer"},
    "halwa": {"halwa"},
    "pickle": {"pickle", "achaar", "achar"},
    "raita": {"raita"},
    "khichdi": {"khichdi"},
    "paratha": {"paratha"},
}

DISH_TYPE_TERMS = {
    "rice": {"rice", "biryani", "pulao", "khichdi"},
    "bread": {"chapati", "roti", "naan", "paratha", "kulcha"},
    "curry": {"curry", "gravy"},
    "idli": {"idli"},
    "dosa": {"dosa"},
    "snack": SNACK_TERMS,
    "dessert": DESSERT_TERMS,
    "drink": {"tea", "kahwa", "lassi", "sharbat", "juice"},
    "condiment": {"chutney", "pickle", "raita"},
}
