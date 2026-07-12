"""Print a compact YouTube ingestion status report."""

from sqlalchemy import text

from services.database.connection import get_engine


def main() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM recipes")).scalar_one()
        print(f"total_recipes={total}")

        print("youtube_source_tracking")
        rows = conn.execute(
            text(
                """
                SELECT source_name, COUNT(*) AS recipe_count
                FROM recipe_source_tracking
                WHERE source_name LIKE 'youtube.%'
                GROUP BY source_name
                ORDER BY source_name
                """
            )
        ).all()
        for source_name, recipe_count in rows:
            print(f"{source_name}={recipe_count}")

        print("latest_youtube_runs")
        run_rows = conn.execute(
            text(
                """
                SELECT run_id, source_name, status, records_found, records_accepted,
                       records_rejected, records_failed
                FROM ingestion_runs
                WHERE source_name LIKE 'youtube.%'
                ORDER BY run_id DESC
                LIMIT 8
                """
            )
        ).all()
        for row in run_rows:
            print("|".join(str(value) for value in row))

        missing_embeddings = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM recipes r
                LEFT JOIN recipe_embeddings e ON e.recipe_id = r.recipe_id
                WHERE e.recipe_id IS NULL
                """
            )
        ).scalar_one()
        print(f"missing_embeddings={missing_embeddings}")


if __name__ == "__main__":
    main()
