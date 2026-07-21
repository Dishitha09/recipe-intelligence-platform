from services.observability.alerts import ValidationAlertDispatcher


class FakeResponse:
    def raise_for_status(self):
        return None


class FakeHttpClient:
    def __init__(self):
        self.posts = []

    def post(self, url, json=None, timeout=None):
        self.posts.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )

        return FakeResponse()


def test_validation_alert_dispatcher_posts_when_threshold_met(monkeypatch):
    monkeypatch.delenv("PAGERDUTY_ROUTING_KEY", raising=False)
    http_client = FakeHttpClient()
    dispatcher = ValidationAlertDispatcher(
        webhook_url="https://hooks.example.test/slack",
        threshold=5,
        http_client=http_client,
    )
    monkeypatch.setattr(dispatcher, "_critical_failure_count", lambda: 5)

    sent = dispatcher.maybe_alert()

    assert sent is True
    assert len(http_client.posts) == 1
    assert "critical validation failures" in http_client.posts[0]["json"]["text"]


def test_validation_alert_dispatcher_is_quiet_below_threshold(monkeypatch):
    monkeypatch.delenv("PAGERDUTY_ROUTING_KEY", raising=False)
    http_client = FakeHttpClient()
    dispatcher = ValidationAlertDispatcher(
        webhook_url="https://hooks.example.test/slack",
        threshold=5,
        http_client=http_client,
    )
    monkeypatch.setattr(dispatcher, "_critical_failure_count", lambda: 4)

    sent = dispatcher.maybe_alert()

    assert sent is False
    assert http_client.posts == []


def test_validation_alert_dispatcher_posts_to_pagerduty(monkeypatch):
    monkeypatch.setenv("PAGERDUTY_ROUTING_KEY", "pd-test-key")
    http_client = FakeHttpClient()
    dispatcher = ValidationAlertDispatcher(
        webhook_url=None,
        threshold=5,
        http_client=http_client,
    )
    monkeypatch.setattr(dispatcher, "_critical_failure_count", lambda: 5)

    sent = dispatcher.maybe_alert()

    assert sent is True
    assert len(http_client.posts) == 1
    assert http_client.posts[0]["url"] == "https://events.pagerduty.com/v2/enqueue"
    assert http_client.posts[0]["json"]["routing_key"] == "pd-test-key"
    assert http_client.posts[0]["json"]["event_action"] == "trigger"
