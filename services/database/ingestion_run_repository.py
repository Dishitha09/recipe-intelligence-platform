import json

from sqlalchemy import text

from services.database.connection import engine


class IngestionRunRepository:
    def start_run(self, source_id, source_name=None, source_type=None):
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO ingestion_runs
                        (source_id, source_name, source_type, status)
                    VALUES
                        (:source_id, :source_name, :source_type, 'RUNNING')
                    RETURNING run_id
                    """
                ),
                {
                    "source_id": source_id,
                    "source_name": source_name or source_id,
                    "source_type": source_type,
                },
            )

            return result.scalar()

    def complete_run(self, run_id, summary):
        if run_id is None:
            return None

        counts = self._counts(summary)

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ingestion_runs
                    SET
                        status = 'COMPLETED',
                        ended_at = CURRENT_TIMESTAMP,
                        records_found = :records_found,
                        records_coerced = :records_coerced,
                        records_accepted = :records_accepted,
                        records_review = :records_review,
                        records_rejected = :records_rejected,
                        records_loaded = :records_loaded,
                        records_failed = :records_failed,
                        summary = CAST(:summary AS jsonb),
                        error_message = NULL
                    WHERE run_id = :run_id
                    """
                ),
                {
                    **counts,
                    "run_id": run_id,
                    "summary": json.dumps(summary, default=str),
                },
            )

        return run_id

    def fail_run(self, run_id, error_message, summary=None):
        if run_id is None:
            return None

        summary = summary or {}
        counts = self._counts(summary)

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ingestion_runs
                    SET
                        status = 'FAILED',
                        ended_at = CURRENT_TIMESTAMP,
                        records_found = :records_found,
                        records_coerced = :records_coerced,
                        records_accepted = :records_accepted,
                        records_review = :records_review,
                        records_rejected = :records_rejected,
                        records_loaded = :records_loaded,
                        records_failed = :records_failed,
                        summary = CAST(:summary AS jsonb),
                        error_message = :error_message
                    WHERE run_id = :run_id
                    """
                ),
                {
                    **counts,
                    "run_id": run_id,
                    "summary": json.dumps(summary, default=str),
                    "error_message": str(error_message),
                },
            )

        return run_id

    def _counts(self, summary):
        def as_count(value):
            if isinstance(value, list):
                return len(value)
            if value is None:
                return 0
            return int(value)

        return {
            "records_found": as_count(summary.get("records_found")),
            "records_coerced": as_count(summary.get("coerced")),
            "records_accepted": as_count(summary.get("accepted")),
            "records_review": as_count(summary.get("review")),
            "records_rejected": as_count(summary.get("rejected")),
            "records_loaded": as_count(summary.get("loaded")),
            "records_failed": (
                as_count(summary.get("dead_letter"))
                + as_count(summary.get("validation_errors"))
            ),
        }
