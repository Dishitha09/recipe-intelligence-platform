import os
from datetime import datetime, timezone

import requests
from sqlalchemy import text

from services.database.connection import engine
from services.reliability.retry import transient_retry


CRITICAL_CHECK_IDS = ("V01", "V02", "V03", "V09")


class ValidationAlertDispatcher:
    def __init__(
        self,
        webhook_url=None,
        threshold=None,
        window_minutes=None,
        http_client=None,
    ):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.pagerduty_routing_key = os.getenv("PAGERDUTY_ROUTING_KEY")
        self.pagerduty_severity = os.getenv("PAGERDUTY_SEVERITY", "critical")
        self.threshold = int(
            threshold
            if threshold is not None
            else os.getenv("CRITICAL_FAILURE_ALERT_THRESHOLD", "5")
        )
        self.window_minutes = int(
            window_minutes
            if window_minutes is not None
            else os.getenv("CRITICAL_FAILURE_WINDOW_MINUTES", "60")
        )
        self.http_client = http_client or requests

    def maybe_alert(self):
        if not self.webhook_url and not self.pagerduty_routing_key:
            return False

        failure_count = self._critical_failure_count()

        if failure_count < self.threshold:
            return False

        payload = {
            "text": (
                "Recipe pipeline critical validation failures: "
                f"{failure_count} in the last {self.window_minutes} minutes."
            ),
            "failure_count": failure_count,
            "threshold": self.threshold,
            "window_minutes": self.window_minutes,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        self._post(payload)
        self._post_pagerduty(payload)

        return True

    def _critical_failure_count(self):
        with engine.connect() as conn:
            return conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM dead_letter_queue
                    WHERE failed_at >= CURRENT_TIMESTAMP
                                      - (:window_minutes * INTERVAL '1 minute')
                      AND reason_codes ?| ARRAY['V01', 'V02', 'V03', 'V09']
                    """
                ),
                {
                    "window_minutes": self.window_minutes,
                },
            ).scalar() or 0

    @transient_retry
    def _post(self, payload):
        if not self.webhook_url:
            return None

        response = self.http_client.post(
            self.webhook_url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return response

    @transient_retry
    def _post_pagerduty(self, payload):
        if not self.pagerduty_routing_key:
            return None

        response = self.http_client.post(
            "https://events.pagerduty.com/v2/enqueue",
            json={
                "routing_key": self.pagerduty_routing_key,
                "event_action": "trigger",
                "dedup_key": "recipe-pipeline-critical-validation-failures",
                "payload": {
                    "summary": payload["text"],
                    "severity": self.pagerduty_severity,
                    "source": "recipe-intelligence-platform",
                    "custom_details": payload,
                },
            },
            timeout=10,
        )
        response.raise_for_status()
        return response
