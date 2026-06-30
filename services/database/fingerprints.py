import hashlib
import json
import re
from typing import Any


VOLATILE_KEYS = {
    "checked_at",
    "created_at",
    "failed_at",
    "ingested_at",
    "record_id",
    "timestamp",
    "updated_at",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value).strip().lower())


def stable_for_hash(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    if isinstance(value, dict):
        return {
            str(key): stable_for_hash(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in VOLATILE_KEYS
        }

    if isinstance(value, (list, tuple, set)):
        return [stable_for_hash(item) for item in value]

    return value


def stable_hash(value: Any) -> str:
    payload = json.dumps(
        stable_for_hash(value),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def recipe_fingerprints(recipe) -> dict:
    source_url = normalize_text(getattr(recipe, "source_url", None))
    ingredients = [
        {
            "name": normalize_text(
                getattr(ingredient, "canonical_name", None)
                or getattr(ingredient, "ingredient_name", None)
            ),
            "quantity": getattr(ingredient, "quantity", None),
            "unit": normalize_text(getattr(ingredient, "unit", None)),
        }
        for ingredient in getattr(recipe, "ingredients", []) or []
    ]
    steps = [
        normalize_text(getattr(step, "instruction", ""))
        for step in getattr(recipe, "steps", []) or []
    ]

    content_hash = stable_hash(
        {
            "title": normalize_text(getattr(recipe, "title", None)),
            "source_url": source_url,
            "ingredients": ingredients,
            "steps": steps,
        }
    )

    return {
        "content_hash": content_hash,
        "source_url_hash": stable_hash(source_url) if source_url else None,
    }
