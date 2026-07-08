import argparse

from sqlalchemy import text

from services.database.connection import engine


NON_ENGLISH_INGREDIENT_PATTERN = "[\u0900-\u097F\u0C80-\u0CFF]"


CHILD_RECIPE_ID_TABLES = (
    "pipeline_audit_log",
    "recipe_embeddings",
    "recipe_ingredients",
    "recipe_ratings_summary",
    "recipe_reviews",
    "recipe_source_tracking",
    "recipe_sources",
    "recipe_steps",
    "review_queue",
    "trending_recipes",
    "validation_reports",
)


def cleanup_source(source_url_prefix, apply=False, prune_no_ingredient_recipes=False):
    source_like = f"{source_url_prefix.rstrip('/')}/%"

    with engine.begin() as conn:
        ingredient_ids = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT ri.recipe_ingredient_id
                    FROM recipe_ingredients ri
                    JOIN recipes r ON r.recipe_id = ri.recipe_id
                    WHERE r.source_url LIKE :source_like
                      AND (
                            ri.ingredient_name ~ :non_english_pattern
                         OR trim(ri.ingredient_name) IN ('-', chr(8211), chr(8212))
                         OR trim(ri.ingredient_name) ~ '^[0-9]+$'
                      )
                    """
                ),
                {
                    "source_like": source_like,
                    "non_english_pattern": NON_ENGLISH_INGREDIENT_PATTERN,
                },
            )
        ]

        no_ingredient_recipe_ids = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT r.recipe_id
                    FROM recipes r
                    WHERE r.source_url LIKE :source_like
                      AND NOT EXISTS (
                          SELECT 1
                          FROM recipe_ingredients ri
                          WHERE ri.recipe_id = r.recipe_id
                      )
                    """
                ),
                {"source_like": source_like},
            )
        ]

        summary = {
            "source_url_prefix": source_url_prefix,
            "bad_ingredient_rows": len(ingredient_ids),
            "no_ingredient_recipes": len(no_ingredient_recipe_ids),
            "dry_run": not apply,
        }

        if not apply:
            return summary

        if ingredient_ids:
            deleted = conn.execute(
                text(
                    """
                    DELETE FROM recipe_ingredients
                    WHERE recipe_ingredient_id = ANY(:ingredient_ids)
                    """
                ),
                {"ingredient_ids": ingredient_ids},
            )
            summary["deleted_bad_ingredient_rows"] = deleted.rowcount
        else:
            summary["deleted_bad_ingredient_rows"] = 0

        if prune_no_ingredient_recipes and no_ingredient_recipe_ids:
            child_deletes = {}
            for table_name in CHILD_RECIPE_ID_TABLES:
                deleted = conn.execute(
                    text(
                        f"""
                        DELETE FROM {table_name}
                        WHERE recipe_id = ANY(:recipe_ids)
                        """
                    ),
                    {"recipe_ids": no_ingredient_recipe_ids},
                )
                child_deletes[table_name] = deleted.rowcount

            variation_delete = conn.execute(
                text(
                    """
                    DELETE FROM recipe_variations
                    WHERE recipe_id = ANY(:recipe_ids)
                       OR canonical_recipe_id = ANY(:recipe_ids)
                    """
                ),
                {"recipe_ids": no_ingredient_recipe_ids},
            )
            child_deletes["recipe_variations"] = variation_delete.rowcount

            recipe_delete = conn.execute(
                text(
                    """
                    DELETE FROM recipes
                    WHERE recipe_id = ANY(:recipe_ids)
                    """
                ),
                {"recipe_ids": no_ingredient_recipe_ids},
            )
            summary["deleted_no_ingredient_recipes"] = recipe_delete.rowcount
            summary["child_deletes"] = child_deletes
        else:
            summary["deleted_no_ingredient_recipes"] = 0

        return summary


def parse_args():
    parser = argparse.ArgumentParser(
        description="Clean localized/junk ingredient rows from scraped web data."
    )
    parser.add_argument("--source-url-prefix", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--prune-no-ingredient-recipes", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    summary = cleanup_source(
        source_url_prefix=args.source_url_prefix,
        apply=args.apply,
        prune_no_ingredient_recipes=args.prune_no_ingredient_recipes,
    )
    print(summary)


if __name__ == "__main__":
    main()
