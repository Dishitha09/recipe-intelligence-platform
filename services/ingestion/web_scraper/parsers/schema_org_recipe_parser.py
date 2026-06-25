import json
from typing import Any, Dict, List, Optional

from scrapy.http import Response


def parse_schema_org_recipe(response: Response) -> Optional[Dict[str, Any]]:
    scripts = response.css("script[type='application/ld+json']::text").getall()

    candidates = []
    for script in scripts:
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue

        candidates.extend(_extract_recipe_objects(payload))

    for candidate in candidates:
        if _is_recipe(candidate):
            return _build_recipe(candidate, response.url)

    return None


def _extract_recipe_objects(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        if _is_recipe(payload):
            return [payload]

        if payload.get("@graph"):
            objects = []
            for item in payload.get("@graph", []):
                objects.extend(_extract_recipe_objects(item))
            return objects

        return []

    if isinstance(payload, list):
        objects = []
        for item in payload:
            objects.extend(_extract_recipe_objects(item))
        return objects

    return []


def _is_recipe(payload: Dict[str, Any]) -> bool:
    recipe_type = payload.get("@type")
    if isinstance(recipe_type, str):
        return recipe_type.lower() == "recipe"

    if isinstance(recipe_type, list):
        return any(str(item).lower() == "recipe" for item in recipe_type)

    return False


def _build_recipe(payload: Dict[str, Any], source_url: str) -> Dict[str, Any]:
    ingredients = payload.get("recipeIngredient") or []
    steps = _parse_recipe_instructions(payload.get("recipeInstructions") or [])

    return {
        "title": payload.get("name") or payload.get("headline"),
        "description": payload.get("description"),
        "source_url": payload.get("url") or source_url,
        "ingredients": ingredients,
        "steps": steps,
        "image": _extract_image(payload),
    }


def _parse_recipe_instructions(instructions: Any) -> List[str]:
    if isinstance(instructions, str):
        return [instructions.strip()] if instructions.strip() else []

    if isinstance(instructions, list):
        parsed = []
        for item in instructions:
            if isinstance(item, str):
                parsed.append(item.strip())
            elif isinstance(item, dict):
                if item.get("@type") == "HowToSection":
                    parsed.extend(_parse_recipe_instructions(item.get("itemListElement", [])))
                else:
                    parsed.append(
                        str(item.get("text") or item.get("name") or "").strip()
                    )
        return [step for step in parsed if step]

    if isinstance(instructions, dict):
        return _parse_recipe_instructions(instructions.get("itemListElement") or [])

    return []


def _extract_image(payload: Dict[str, Any]) -> Optional[str]:
    image = payload.get("image")
    if isinstance(image, str):
        return image
    if isinstance(image, list) and image:
        return image[0]
    if isinstance(image, dict):
        return image.get("url")
    return None
