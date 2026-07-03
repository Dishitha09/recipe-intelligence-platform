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
