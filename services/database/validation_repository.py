import json

from sqlalchemy import text

from services.database.connection import engine


class ValidationRepository:
    def save_report(self, recipe_id, report, message=None):
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO validation_reports
                        (
                            recipe_id,
                            status,
                            validation_message,
                            check_results,
                            flags,
                            summary
                        )
                    VALUES
                        (
                            :recipe_id,
                            :status,
                            :validation_message,
                            CAST(:check_results AS jsonb),
                            CAST(:flags AS jsonb),
                            CAST(:summary AS jsonb)
                        )
                    RETURNING validation_id
                    """
                ),
                {
                    "recipe_id": recipe_id,
                    "status": report.status,
                    "validation_message": message or report.status,
                    "check_results": json.dumps(
                        [
                            result.model_dump(mode="json")
                            for result in report.check_results
                        ]
                    ),
                    "flags": json.dumps(report.flags),
                    "summary": json.dumps(report.summary),
                },
            )

            return result.scalar()

    def save_review(self, record_id, recipe, report, reason=None):
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO review_queue
                        (
                            record_id,
                            reason,
                            validation_report,
                            status
                        )
                    VALUES
                        (
                            CAST(:record_id AS uuid),
                            :reason,
                            CAST(:validation_report AS jsonb),
                            'PENDING'
                        )
                    RETURNING review_id
                    """
                ),
                {
                    "record_id": record_id,
                    "reason": reason or self._failure_summary(report),
                    "validation_report": json.dumps(
                        {
                            "recipe": recipe.model_dump(mode="json"),
                            "report": report.model_dump(mode="json"),
                        }
                    ),
                },
            )

            return result.scalar()

    def save_dead_letter(
        self,
        source_type,
        raw_payload,
        error_message,
        record_id=None,
        validation_report=None,
    ):
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO dead_letter_queue
                        (
                            source_type,
                            record_id,
                            raw_payload,
                            error_message,
                            validation_report
                        )
                    VALUES
                        (
                            :source_type,
                            CAST(:record_id AS uuid),
                            CAST(:raw_payload AS jsonb),
                            :error_message,
                            CAST(:validation_report AS jsonb)
                        )
                    RETURNING dlq_id
                    """
                ),
                {
                    "source_type": source_type,
                    "record_id": record_id,
                    "raw_payload": json.dumps(raw_payload),
                    "error_message": error_message,
                    "validation_report": json.dumps(validation_report)
                    if validation_report is not None
                    else None,
                },
            )

            return result.scalar()

    def _failure_summary(self, report):
        failures = [
            f"{result.check_id}: {result.message}"
            for result in report.check_results
            if not result.passed
        ]

        return "; ".join(failures) if failures else report.status
