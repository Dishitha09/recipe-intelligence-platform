import argparse
import csv
from pathlib import Path

from services.pipeline.recipe_pipeline import RecipePipeline


DEFAULT_OUTPUT = Path(
    "data/datasets/generated/indian_recipes_100.csv"
)


REGIONAL_RECIPES = [
    ("Masala Dosa", "South Indian", "Karnataka", "South"),
    ("Paneer Butter Masala", "North Indian", "Punjab", "North"),
    ("Chole Masala", "North Indian", "Punjab", "North"),
    ("Aloo Gobi", "North Indian", "Uttar Pradesh", "North"),
    ("Tomato Rice", "South Indian", "Tamil Nadu", "South"),
    ("Moong Dal Khichdi", "Indian", "Gujarat", "West"),
    ("Rajma Rice", "North Indian", "Delhi", "North"),
    ("Besan Chilla", "North Indian", "Rajasthan", "North"),
    ("Curd Rice", "South Indian", "Tamil Nadu", "South"),
    ("Vegetable Pulao", "Indian", "Telangana", "South"),
    ("Kadhi Pakora", "North Indian", "Rajasthan", "North"),
    ("Dal Tadka", "North Indian", "Punjab", "North"),
    ("Jeera Rice", "Indian", "Maharashtra", "West"),
    ("Paneer Bhurji", "North Indian", "Delhi", "North"),
    ("Potato Curry", "Indian", "West Bengal", "East"),
    ("Cauliflower Sabzi", "Indian", "Bihar", "East"),
    ("Urad Dal Vada", "South Indian", "Tamil Nadu", "South"),
    ("Sambar Rice", "South Indian", "Karnataka", "South"),
    ("Tomato Chutney", "South Indian", "Andhra Pradesh", "South"),
    ("Chickpea Sundal", "South Indian", "Kerala", "South"),
]


INGREDIENT_SETS = [
    ["200 g rice", "50 g urad dal", "5 g salt", "15 ml oil"],
    ["200 g paneer", "150 g tomato", "100 g onion", "20 g butter"],
    ["200 g chickpea", "120 g onion", "150 g tomato", "10 g turmeric"],
    ["200 g potato", "150 g cauliflower", "100 g onion", "10 g cumin"],
    ["250 g rice", "150 g tomato", "10 g mustard seed", "15 ml oil"],
    ["200 g rice", "100 g moong dal", "5 g salt", "10 g ghee"],
    ["200 g rice", "150 g chickpea", "100 g onion", "10 g cumin"],
    ["150 g besan", "80 g onion", "10 g coriander", "10 ml oil"],
    ["250 g rice", "150 g yogurt", "5 g salt", "10 g mustard seed"],
    ["250 g rice", "100 g potato", "80 g onion", "15 ml oil"],
]


STEPS = [
    "Wash and prepare all ingredients",
    "Cook the base ingredients until tender",
    "Add spices and simmer until flavors combine",
    "Finish with seasoning and serve hot",
]


def build_rows(count):
    rows = []

    for index in range(count):
        name, cuisine, state, region = REGIONAL_RECIPES[
            index % len(REGIONAL_RECIPES)
        ]
        batch_number = index // len(REGIONAL_RECIPES) + 1
        title = f"{name} Scale Batch {batch_number:02d}"

        rows.append(
            {
                "title": title,
                "description": (
                    f"Production scale ingestion fixture for {name}."
                ),
                "cuisine": cuisine,
                "state": state,
                "region": region,
                "language": "english",
                "source_url": (
                    "https://example.com/generated-indian-recipes/"
                    f"{index + 1:04d}"
                ),
                "ingredients": "|".join(
                    INGREDIENT_SETS[index % len(INGREDIENT_SETS)]
                ),
                "steps": "|".join(STEPS),
            }
        )

    return rows


def write_dataset(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "title",
                "description",
                "cuisine",
                "state",
                "region",
                "language",
                "source_url",
                "ingredients",
                "steps",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def ingest_dataset(output_path, chunk_size):
    pipeline = RecipePipeline()
    totals = {
        "coerced": 0,
        "enriched": 0,
        "accepted": 0,
        "review": 0,
        "loaded": 0,
        "rejected": 0,
        "validation_reports": 0,
    }

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    for start in range(0, len(rows), chunk_size):
        chunk = rows[start:start + chunk_size]
        chunk_path = output_path.with_name(
            f"{output_path.stem}_chunk_{start // chunk_size + 1:03d}.csv"
        )
        write_dataset(chunk, chunk_path)
        summary = pipeline.run_csv_pipeline(str(chunk_path))

        for key in totals:
            value = summary.get(key, 0)

            if isinstance(value, list):
                value = len(value)

            totals[key] += value

    return totals


def main():
    parser = argparse.ArgumentParser(
        description="Generate and optionally ingest a 100+ Indian recipe CSV."
    )
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument("--chunk-size", type=int, default=25)
    parser.add_argument("--ingest", action="store_true")
    args = parser.parse_args()

    rows = build_rows(args.count)
    write_dataset(rows, args.output)
    print(f"Generated {len(rows)} recipes at {args.output}")

    if args.ingest:
        totals = ingest_dataset(args.output, args.chunk_size)
        print(f"Ingestion summary: {totals}")


if __name__ == "__main__":
    main()
