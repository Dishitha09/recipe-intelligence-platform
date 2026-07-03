import json
import logging

from sqlalchemy import text

from services.database.connection import engine
from services.database.fingerprints import stable_hash
from services.observability.alerts import ValidationAlertDispatcher
from services.reliability.retry import transient_retry


logger = logging.getLogger(__name__)


class ValidationRepository:
    def list_pending_reviews(self, limit=100):
        with engine.connect() as conn:
            return conn.execute(
                text(
                    """
                    SELECT review_id, recipe_id, record_id, reason,
                           reason_codes, validation_report, created_at
                    FROM review_queue
                    WHERE status = 'PENDING'
                    ORDER BY created_at ASC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()

    def mark_review_resolved(self, review_id, status="RESOLVED"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE review_queue
                    SET status = :status
                    WHERE review_id = :review_id
                    """
                ),
                {"review_id": review_id, "status": status},
            )

    def list_dead_letters(self, limit=100):
        with engine.connect() as conn:
            return conn.execute(
                text(
                    """
                    SELECT dlq_id, source_type, record_id, error_message,
                           reason_code, reason_codes, failed_at
                    FROM dead_letter_queue
                    ORDER BY failed_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()

    @transient_retry
    def save_report(self, recipe_id, report, message=None):
        check_results = [
            result.model_dump(mode="json")
            for result in report.check_results
        ]
        failure_codes = self._failure_codes(report)
        payload = {
            "recipe_id": recipe_id,
            "status": report.status,
            "validation_message": message or report.status,
            "failure_codes": failure_codes,
            "check_results": check_results,
            "flags": report.flags,
            "summary": report.summary,
        }
        report_hash = stable_hash(payload)

        with engine.begin() as conn:
            existing_id = conn.execute(
                text(
                    """
                    SELECT validation_id
                    FROM validation_reports
                    WHERE report_hash = :report_hash
                    LIMIT 1
                    """
                ),
                {"report_hash": report_hash},
            ).scalar()

            if existing_id is not None:
                return existing_id

            result = conn.execute(
                text(
                    """
                    INSERT INTO validation_reports
                        (
                            recipe_id,
                            status,
                            validation_message,
                            failure_codes,
                            check_results,
                            flags,
                            summary,
                            report_hash
                        )
                    VALUES
                        (
                            :recipe_id,
                            :status,
                            :validation_message,
                            CAST(:failure_codes AS jsonb),
                            CAST(:check_results AS jsonb),
                            CAST(:flags AS jsonb),
                            CAST(:summary AS jsonb),
                            :report_hash
                        )
                    RETURNING validation_id
                    """
                ),
                {
                    "recipe_id": recipe_id,
                    "status": payload["status"],
                    "validation_message": payload["validation_message"],
                    "failure_codes": json.dumps(failure_codes),
                    "check_results": json.dumps(check_results),
                    "flags": json.dumps(payload["flags"]),
                    "summary": json.dumps(payload["summary"]),
                    "report_hash": report_hash,
                },
            )

            dlq_id = result.scalar()

        self._alert_on_critical_failures()

        return dlq_id

    @transient_retry
    def save_review(self, record_id, recipe, report, reason=None, recipe_id=None):
        reason_codes = self._failure_codes(report)
        review_payload = {
            "recipe": recipe.model_dump(mode="json"),
            "report": report.model_dump(mode="json"),
        }
        review_hash = stable_hash(
            {
                "recipe_id": recipe_id,
                "source_url": getattr(recipe, "source_url", None),
                "title": getattr(recipe, "title", None),
                "reason": reason or self._failure_summary(report),
                "reason_codes": reason_codes,
            }
        )

        with engine.begin() as conn:
            existing_id = conn.execute(
                text(
                    """
                    SELECT review_id
                    FROM review_queue
                    WHERE review_hash = :review_hash
                    LIMIT 1
                    """
                ),
                {"review_hash": review_hash},
            ).scalar()

            if existing_id is not None:
                return existing_id

            result = conn.execute(
                text(
                    """
                    INSERT INTO review_queue
                        (
                            recipe_id,
                            record_id,
                            reason,
                            reason_codes,
                            validation_report,
                            review_hash,
                            status
                        )
                    VALUES
                        (
                            :recipe_id,
                            CAST(:record_id AS uuid),
                            :reason,
                            CAST(:reason_codes AS jsonb),
                            CAST(:validation_report AS jsonb),
                            :review_hash,
                            'PENDING'
                        )
                    RETURNING review_id
                    """
                ),
                {
                    "recipe_id": recipe_id,
                    "record_id": record_id,
                    "reason": reason or self._failure_summary(report),
                    "reason_codes": json.dumps(reason_codes),
                    "validation_report": json.dumps(review_payload),
                    "review_hash": review_hash,
                },
            )

            return result.scalar()

    @transient_retry
    def save_dead_letter(
        self,
        source_type,
        raw_payload,
        error_message,
        record_id=None,
        validation_report=None,
    ):
        reason_codes = self._reason_codes(validation_report)
        reason_code = reason_codes[0] if reason_codes else "UNCLASSIFIED"
        dead_letter_hash = stable_hash(
            {
                "source_type": source_type,
                "raw_payload": raw_payload,
                "error_message": error_message,
                "reason_codes": reason_codes,
                "validation_report": validation_report,
            }
        )

        with engine.begin() as conn:
            existing_id = conn.execute(
                text(
                    """
                    SELECT dlq_id
                    FROM dead_letter_queue
                    WHERE dead_letter_hash = :dead_letter_hash
                    LIMIT 1
                    """
                ),
                {"dead_letter_hash": dead_letter_hash},
            ).scalar()

            if existing_id is not None:
                return existing_id

            result = conn.execute(
                text(
                    """
                    INSERT INTO dead_letter_queue
                        (
                            source_type,
                            record_id,
                            raw_payload,
                            error_message,
                            reason_code,
                            reason_codes,
                            validation_report,
                            dead_letter_hash
                        )
                    VALUES
                        (
                            :source_type,
                            CAST(:record_id AS uuid),
                            CAST(:raw_payload AS jsonb),
                            :error_message,
                            :reason_code,
                            CAST(:reason_codes AS jsonb),
                            CAST(:validation_report AS jsonb),
                            :dead_letter_hash
                        )
                    RETURNING dlq_id
                    """
                ),
                {
                    "source_type": source_type,
                    "record_id": record_id,
                    "raw_payload": json.dumps(raw_payload),
                    "error_message": error_message,
                    "reason_code": reason_code,
                    "reason_codes": json.dumps(reason_codes),
                    "validation_report": json.dumps(validation_report)
                    if validation_report is not None
                    else None,
                    "dead_letter_hash": dead_letter_hash,
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

    def _failure_codes(self, report):
        if report is None:
            return []

        return [
            result.check_id
            for result in report.check_results
            if not result.passed
        ]

    def _reason_codes(self, validation_report):
        if validation_report is None:
            return []

        if hasattr(validation_report, "check_results"):
            return self._failure_codes(validation_report)

        if isinstance(validation_report, dict):
            results = validation_report.get("check_results") or []
            return [
                result.get("check_id")
                for result in results
                if isinstance(result, dict) and not result.get("passed", True)
            ]

        return []

    def _alert_on_critical_failures(self):
        try:
            ValidationAlertDispatcher().maybe_alert()
        except Exception as exc:
            logger.warning(
                "Critical validation alert dispatch failed: %s",
                exc,
            )
