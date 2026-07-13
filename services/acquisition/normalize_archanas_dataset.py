import argparse
import csv
import re
from pathlib import Path

import pandas as pd

from services.reports.cleanup_non_indian_non_english_recipes import (
    HINDI_MARKER_RE,
    HINDI_MOJIBAKE_RE,
    INDIC_RE,
    is_indian_cuisine,
)


DEFAULT_INPUT = (
    "data/datasets/external/indian_food_dataset_generation/"
    "IndianFoodDatasetCSV.csv"
)
DEFAULT_OUTPUT = (
    "data/datasets/external/indian_food_dataset_generation/"
    "archanas_kitchen_recipes_normalized.csv"
)


def clean_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_ingredients(value):
    text = clean_text(value)

    if not text:
        return ""

    parts = [
        clean_text(part)
        for part in re.split(r"\s*,\s*", text)
        if clean_text(part)
    ]
    return " | ".join(parts)


def split_instruction_steps(value):
    text = clean_text(value)

    if not text:
        return ""

    text = re.sub(r"(?<=[.!?])(?=[A-Z])", " ", text)
    text = re.sub(
        r"\b(Once|After|Then|Next|Now|Add|Heat|Serve|Transfer|Turn off|"
        r"Finally)\b",
        r"| \1",
        text,
    )
    candidates = re.split(r"\||(?<=[.!?])\s+", text)
    steps = []

    for candidate in candidates:
        step = clean_text(candidate)

        if not step:
            continue

        if len(step) < 8 and steps:
            steps[-1] = f"{steps[-1]} {step}"
            continue

        steps.append(step)

    return " | ".join(steps)


def is_source_truth_english_indian(row, title, ingredients, steps, source_url):
    text_blob = " ".join(
        [
            title,
            ingredients,
            steps,
            source_url,
            clean_text(row.get("RecipeName")),
            clean_text(row.get("Instructions")),
            clean_text(row.get("TranslatedInstructions")),
        ]
    )

    if HINDI_MARKER_RE.search(f"{title} {source_url}"):
        return False

    if HINDI_MOJIBAKE_RE.search(text_blob) or INDIC_RE.search(text_blob):
        return False

    return is_indian_cuisine(clean_text(row.get("Cuisine")))


def normalize_archanas_dataset(input_path=DEFAULT_INPUT, output_path=DEFAULT_OUTPUT):
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, dtype=str).fillna("")
    rows = []

    for index, row in df.iterrows():
        title = clean_text(row.get("TranslatedRecipeName")) or clean_text(
            row.get("RecipeName")
        )
        ingredients = split_ingredients(
            row.get("TranslatedIngredients") or row.get("Ingredients")
        )
        steps = split_instruction_steps(
            row.get("TranslatedInstructions") or row.get("Instructions")
        )
        source_url = clean_text(row.get("URL"))

        if not title or not ingredients or not steps or not source_url:
            continue

        if not is_source_truth_english_indian(
            row,
            title,
            ingredients,
            steps,
            source_url,
        ):
            continue

        rows.append(
            {
                "title": title,
                "original_title": clean_text(row.get("RecipeName")),
                "translated_title": clean_text(row.get("TranslatedRecipeName")),
                "description": " | ".join(
                    item
                    for item in [
                        clean_text(row.get("Cuisine")),
                        clean_text(row.get("Course")),
                        clean_text(row.get("Diet")),
                    ]
                    if item
                ),
                "cuisine": clean_text(row.get("Cuisine")),
                "language": "english",
                "source_url": source_url,
                "ingredients": ingredients,
                "instructions": steps,
                "prep_time_minutes": clean_text(row.get("PrepTimeInMins")),
                "cook_time_minutes": clean_text(row.get("CookTimeInMins")),
                "total_time_minutes": clean_text(row.get("TotalTimeInMins")),
                "servings": clean_text(row.get("Servings")),
                "course": clean_text(row.get("Course")),
                "diet": clean_text(row.get("Diet")),
                "external_dataset_row": clean_text(row.get("Srno")) or str(index + 1),
            }
        )

    fields = [
        "title",
        "original_title",
        "translated_title",
        "description",
        "cuisine",
        "language",
        "source_url",
        "ingredients",
        "instructions",
        "prep_time_minutes",
        "cook_time_minutes",
        "total_time_minutes",
        "servings",
        "course",
        "diet",
        "external_dataset_row",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "input": str(input_path),
        "output": str(output_path),
        "input_rows": len(df),
        "output_rows": len(rows),
        "dropped_rows": len(df) - len(rows),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normalize IndianFoodDatasetGeneration CSV for ingestion."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    print(normalize_archanas_dataset(args.input, args.output))


if __name__ == "__main__":
    main()
