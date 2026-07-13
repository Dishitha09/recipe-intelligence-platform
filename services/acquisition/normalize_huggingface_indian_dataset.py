import argparse
import csv
from pathlib import Path

import pandas as pd

from services.acquisition.normalize_archanas_dataset import (
    clean_text,
    is_source_truth_english_indian,
    split_ingredients,
    split_instruction_steps,
)


DEFAULT_INPUT = (
    "data/datasets/huggingface_indian/raw/"
    "Anupam007__indian-recipe-dataset__Cleaned_Indian_Food_Dataset.csv"
)
DEFAULT_OUTPUT = (
    "data/datasets/huggingface_indian/processed/"
    "anupam007_indian_recipe_dataset_normalized.csv"
)


def normalize_huggingface_indian_dataset(
    input_path=DEFAULT_INPUT,
    output_path=DEFAULT_OUTPUT,
    dataset_source="Anupam007/indian-recipe-dataset",
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, dtype=str).fillna("")
    rows = []

    for index, row in df.iterrows():
        title = clean_text(row.get("TranslatedRecipeName"))
        ingredients = split_ingredients(row.get("TranslatedIngredients"))
        steps = split_instruction_steps(row.get("TranslatedInstructions"))
        source_url = clean_text(row.get("URL"))
        cuisine = clean_text(row.get("Cuisine"))
        image_url = clean_text(row.get("image-url"))

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
                "description": cuisine,
                "cuisine": cuisine,
                "language": "english",
                "source_url": source_url,
                "ingredients": ingredients,
                "instructions": steps,
                "prep_time_min": clean_text(row.get("PrepTimeInMins")),
                "cook_time_min": clean_text(row.get("CookTimeInMins")),
                "total_time_min": clean_text(row.get("TotalTimeInMins")),
                "servings": clean_text(row.get("Servings")),
                "course": clean_text(row.get("Course")),
                "diet": clean_text(row.get("Diet")),
                "image_url": image_url,
                "external_dataset_row": str(index + 1),
                "dataset_source": dataset_source,
            }
        )

    fields = [
        "title",
        "description",
        "cuisine",
        "language",
        "source_url",
        "ingredients",
        "instructions",
        "prep_time_min",
        "cook_time_min",
        "total_time_min",
        "servings",
        "course",
        "diet",
        "image_url",
        "external_dataset_row",
        "dataset_source",
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
        description="Normalize Hugging Face Indian recipe CSV source data."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--dataset-source",
        default="Anupam007/indian-recipe-dataset",
    )
    args = parser.parse_args()

    print(
        normalize_huggingface_indian_dataset(
            args.input,
            args.output,
            dataset_source=args.dataset_source,
        )
    )


if __name__ == "__main__":
    main()
