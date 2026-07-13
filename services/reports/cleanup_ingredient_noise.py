"""Remove strict quantity/unit-only ingredient rows from loaded recipes."""

import argparse

from sqlalchemy import text

from services.database.connection import engine


NOISE_PATTERNS = (
    r"^\s*$",
    r"^\s*[-–—()]+\s*$",
    r"^\s*\(?optional\)?\s*$",
    r"^\s*[0-9]+(?:\s*[./-]\s*[0-9]+)?\s*$",
    r"^\s*[0-9]+\s+[0-9]+(?:\s*(?:tsp|tbsp|teaspoons?|tablespoons?|cups?|kg|g|ml|inch))?\s*$",
    r"^\s*(?:[0-9]+(?:\s*[./-]\s*[0-9]+)?\s*)?(?:tsp|tbsp|teaspoons?|tablespoons?|cups?|nos?|pcs|pieces?)\s*$",
    r"^\s*to\s+[0-9]+\s*$",
    r"^\s*of\s+[0-9]+\s+[0-9]+\s+lemons?\s*$",
)


def cleanup_noise(apply=False):
    pattern_sql = " OR ".join(
        f"trim(lower(ingredient_name)) ~ :pattern_{index}"
        for index, _ in enumerate(NOISE_PATTERNS)
    )
    params = {
        f"pattern_{index}": pattern
        for index, pattern in enumerate(NOISE_PATTERNS)
    }

    with engine.begin() as conn:
        bad_ids = [
            row[0]
            for row in conn.execute(
                text(
                    f"""
                    SELECT recipe_ingredient_id
                    FROM recipe_ingredients
                    WHERE ingredient_name IS NULL
                       OR ({pattern_sql})
                    """
                ),
                params,
            )
        ]

        summary = {
            "bad_ingredient_rows": len(bad_ids),
            "dry_run": not apply,
        }

        if not apply or not bad_ids:
            summary["deleted_bad_ingredient_rows"] = 0
            return summary

        deleted = conn.execute(
            text(
                """
                DELETE FROM recipe_ingredients
                WHERE recipe_ingredient_id = ANY(:bad_ids)
                """
            ),
            {"bad_ids": bad_ids},
        )
        summary["deleted_bad_ingredient_rows"] = deleted.rowcount
        return summary


def main():
    parser = argparse.ArgumentParser(
        description="Clean strict quantity/unit-only ingredient rows."
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(cleanup_noise(apply=args.apply))


if __name__ == "__main__":
    main()
