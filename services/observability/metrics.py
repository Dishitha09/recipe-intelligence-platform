from sqlalchemy import text

from services.database.connection import engine


class PipelineMetricsRepository:
    def snapshot(self):
        with engine.connect() as conn:
            recipes_total = self._scalar(conn, "SELECT count(*) FROM recipes")
            ingredients_total = self._scalar(
                conn,
                "SELECT count(*) FROM recipe_ingredients",
            )
            accepted_reports = self._scalar(
                conn,
                """
                SELECT count(*)
                FROM validation_reports
                WHERE status = 'ACCEPTED'
                """,
            )
            validation_reports = self._scalar(
                conn,
                "SELECT count(*) FROM validation_reports",
            )
            dead_letters = self._scalar(
                conn,
                "SELECT count(*) FROM dead_letter_queue",
            )
            unresolved_ingredients = self._scalar(
                conn,
                """
                SELECT count(*)
                FROM recipe_ingredients
                WHERE canonical_name IS NULL
                   OR enrichment_flags ? 'unresolved_ingredient'
                """,
            )
            uom_conflicts = self._scalar(
                conn,
                """
                SELECT count(*)
                FROM recipe_ingredients
                WHERE enrichment_flags ? 'uom_conflict'
                """,
            )
            failed_runs = self._scalar(
                conn,
                """
                SELECT count(*)
                FROM ingestion_runs
                WHERE status = 'FAILED'
                """,
            )
            avg_latency_seconds = self._scalar(
                conn,
                """
                SELECT COALESCE(
                    AVG(EXTRACT(EPOCH FROM (ended_at - started_at))),
                    0
                )
                FROM ingestion_runs
                WHERE ended_at IS NOT NULL
                """,
            )

        return {
            "records_ingested_total": recipes_total,
            "recipe_ingredients_total": ingredients_total,
            "validation_acceptance_rate": self._rate(
                accepted_reports,
                validation_reports,
            ),
            "ingredient_resolution_rate": self._rate(
                ingredients_total - unresolved_ingredients,
                ingredients_total,
            ),
            "uom_conflict_rate": self._rate(uom_conflicts, ingredients_total),
            "dead_letter_rate": self._rate(
                dead_letters,
                recipes_total + dead_letters,
            ),
            "scraper_failed_runs_total": failed_runs,
            "pipeline_e2e_latency_seconds_avg": float(avg_latency_seconds or 0),
        }

    def _scalar(self, conn, sql):
        return conn.execute(text(sql)).scalar() or 0

    def _rate(self, numerator, denominator):
        if not denominator:
            return 0.0

        return round(float(numerator) / float(denominator), 4)
