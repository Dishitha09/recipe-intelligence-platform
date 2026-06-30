import argparse

from sqlalchemy import text

from services.database.connection import engine
from services.enrichment.state.state_classifier import RecipeStateClassifier
from services.preprocessing.schema_models import Recipe


def backfill_states(limit=None, only_unclassified=False):
    classifier = RecipeStateClassifier()
    where_clause = ""

    if only_unclassified:
        where_clause = "WHERE state IS NULL OR region IS NULL"

    limit_clause = ""
    params = {}
    if limit is not None:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT recipe_id, title, description, cuisine, state, region,
                       source_type, source_url, language
                FROM recipes
                {where_clause}
                ORDER BY recipe_id
                {limit_clause}
                """
            ),
            params,
        ).mappings().all()

        updated = 0
        for row in rows:
            recipe = Recipe(
                title=row["title"],
                description=row["description"],
                cuisine=row["cuisine"],
                state=row["state"],
                region=row["region"],
                source_type=row["source_type"] or "unknown",
                source_url=row["source_url"],
                language=row["language"],
                ingredients=[],
                steps=[],
            )
            result = classifier.classify(recipe)

            conn.execute(
                text(
                    """
                    UPDATE recipes
                    SET
                        state = :state,
                        region = :region,
                        state_confidence = :state_confidence,
                        state_method = :state_method,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE recipe_id = :recipe_id
                    """
                ),
                {
                    "recipe_id": row["recipe_id"],
                    "state": result.state,
                    "region": result.region,
                    "state_confidence": result.confidence,
                    "state_method": result.method,
                },
            )
            updated += 1

    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Backfill recipe state/region classification."
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only-unclassified", action="store_true")
    args = parser.parse_args()

    updated = backfill_states(
        limit=args.limit,
        only_unclassified=args.only_unclassified,
    )
    print(f"Backfilled state classification for {updated} recipes")


if __name__ == "__main__":
    main()
