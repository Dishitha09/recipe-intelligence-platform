import json
import re
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
            recipe = _build_recipe(candidate, response.url)
            html_steps = _extract_html_instruction_steps(response)

            if _is_better_instruction_set(html_steps, recipe["steps"]):
                recipe["steps"] = html_steps
                recipe["instruction_source"] = "html_article"
            else:
                recipe["instruction_source"] = "schema_org"

            return recipe

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
                item_type = item.get("@type")
                item_types = (
                    item_type
                    if isinstance(item_type, list)
                    else [item_type]
                )

                if "HowToSection" in item_types:
                    parsed.extend(
                        _parse_recipe_instructions(
                            item.get("itemListElement", [])
                        )
                    )
                elif item.get("itemListElement"):
                    parsed.extend(
                        _parse_recipe_instructions(
                            item.get("itemListElement", [])
                        )
                    )
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


def _extract_html_instruction_steps(response: Response) -> List[str]:
    candidates = []

    card_steps = _extract_recipe_card_steps(response)
    if card_steps:
        candidates.append(card_steps)

    article_steps = _extract_heading_section_steps(response)
    if article_steps:
        candidates.append(article_steps)

    if not candidates:
        return []

    return max(candidates, key=_instruction_score)


def _extract_recipe_card_steps(response: Response) -> List[str]:
    selectors = (
        "div.wprm-recipe-instruction-text, "
        "li.wprm-recipe-instruction, "
        "ol.recipe-instructions li, "
        "div.instructions li, "
        "[itemprop='recipeInstructions'] li"
    )

    return _dedupe_steps(
        _clean_instruction_text(_selector_text(element))
        for element in response.css(selectors)
    )


def _extract_heading_section_steps(response: Response) -> List[str]:
    combined_steps = []
    past_recipe_card = False

    for heading in response.xpath("//*[self::h2 or self::h3 or self::h4]"):
        heading_text = _selector_text(heading)
        normalized_heading = heading_text.lower()

        if "recipe card" in normalized_heading:
            past_recipe_card = True
            continue

        if past_recipe_card:
            continue

        if not _is_instruction_heading(heading_text):
            continue

        steps = []

        for node in heading.xpath("following-sibling::*"):
            tag_name = (node.xpath("name()").get() or "").lower()
            node_text = _selector_text(node)

            if tag_name in {"h2", "h3", "h4"}:
                if steps:
                    break

                if _is_stop_heading(node_text):
                    break

                continue

            if tag_name in {"script", "style", "figure", "picture", "img"}:
                continue

            list_steps = _extract_list_item_steps(node)

            if list_steps:
                steps.extend(list_steps)
                continue

            instruction, is_numbered = _instruction_from_section_text(
                node_text,
                bool(steps),
            )

            if instruction:
                if (
                    not is_numbered
                    and _should_append_to_previous(instruction, steps)
                ):
                    steps[-1] = f"{steps[-1]} {instruction}"
                else:
                    steps.append(instruction)

        steps = _dedupe_steps(steps)

        if steps:
            combined_steps.extend(steps)

    return _dedupe_steps(combined_steps)


def _extract_list_item_steps(node) -> List[str]:
    steps = []

    for item in node.css("li"):
        text = _clean_instruction_text(_selector_text(item))

        if text and _looks_like_instruction(text):
            steps.append(text)

    return _dedupe_steps(steps)


def _instruction_from_section_text(
    text: str,
    already_collecting: bool,
) -> tuple[str, bool]:
    text = _clean_instruction_text(text)

    if not text or _is_noise_instruction(text):
        return "", False

    numbered = re.match(r"^\s*(?:step\s*)?\d+[\).\s:-]+(.+)$", text, re.I)

    if numbered:
        return _clean_instruction_text(numbered.group(1)), True

    if already_collecting and _looks_like_instruction(text):
        return text, False

    if _looks_like_prep_instruction(text):
        return text, False

    return "", False


def _is_better_instruction_set(candidate: List[str], existing: List[str]) -> bool:
    if not candidate:
        return False

    if not existing:
        return True

    candidate_chars, candidate_count = _instruction_score(candidate)
    existing_chars, existing_count = _instruction_score(existing)

    return (
        candidate_count > existing_count
        and candidate_chars >= existing_chars
    ) or candidate_chars >= existing_chars + 180


def _instruction_score(steps: List[str]):
    return sum(len(step) for step in steps), len(steps)


def _is_instruction_heading(text: str) -> bool:
    normalized = text.lower()
    return any(
        keyword in normalized
        for keyword in (
            "how to",
            "instructions",
            "method",
            "directions",
            "step by step",
            "photo guide",
            "preparation",
        )
    )


def _is_stop_heading(text: str) -> bool:
    normalized = text.lower()
    return any(
        keyword in normalized
        for keyword in (
            "recipe card",
            "variations",
            "related",
            "video",
            "nutrition",
            "notes",
            "comments",
            "about",
            "popular",
            "collections",
        )
    )


def _looks_like_instruction(text: str) -> bool:
    if _is_noise_instruction(text):
        return False

    normalized = text.lower()
    return any(
        verb in normalized
        for verb in (
            "add",
            "bake",
            "blend",
            "boil",
            "chop",
            "cook",
            "drain",
            "fry",
            "grind",
            "heat",
            "knead",
            "mix",
            "pour",
            "remove",
            "rinse",
            "saute",
            "sauté",
            "serve",
            "simmer",
            "soak",
            "sprinkle",
            "steam",
            "stir",
            "temper",
            "turn",
            "wash",
            "whisk",
        )
    )


def _looks_like_prep_instruction(text: str) -> bool:
    if _is_noise_instruction(text):
        return False

    normalized = text.lower()
    return len(text) >= 40 and any(
        verb in normalized
        for verb in (
            "clean",
            "discard",
            "drain",
            "pat dry",
            "rinse",
            "trim",
            "wash",
        )
    )


def _should_append_to_previous(instruction: str, steps: List[str]) -> bool:
    return bool(steps) and len(instruction) < 120 and not re.match(
        r"^(add|bake|blend|boil|cook|fry|heat|mix|pour|rinse|soak|stir)",
        instruction,
        re.I,
    )


def _is_noise_instruction(text: str) -> bool:
    normalized = text.lower()
    return any(
        phrase in normalized
        for phrase in (
            "add your own private notes",
            "here are some dishes",
            "jump to recipe",
            "mention @",
            "prevent sleep mode",
            "private notes",
            "related recipes",
            "tried this recipe",
            "go well with this",
        )
    )


def _selector_text(selector) -> str:
    return " ".join(
        item.strip()
        for item in selector.css("::text").getall()
        if item.strip()
    )


def _clean_instruction_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = re.sub(r"^[\u2022\u25a2\u25a3\u25aa\-\s]+", "", text)
    text = re.sub(r"^Prevent Sleep Mode\s*", "", text, flags=re.I)
    return text.strip()


def _dedupe_steps(values) -> List[str]:
    steps = []
    seen = set()

    for value in values:
        text = _clean_instruction_text(value)

        if not text:
            continue

        key = text.casefold()

        if key in seen:
            continue

        seen.add(key)
        steps.append(text)

    return steps
