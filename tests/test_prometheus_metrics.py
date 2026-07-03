from services.observability.prometheus import build_prometheus_metrics


class FakeMetricsRepository:
    def snapshot(self):
        return {
            "records_ingested_total": 12,
            "preprocessing_pass_rate": 0.9,
            "ingredient_resolution_rate": 0.8,
            "validation_acceptance_rate": 0.7,
            "pipeline_e2e_latency_p99": 4.2,
            "dead_letter_rate": 0.1,
            "llm_calls_per_batch": 2,
        }


def test_build_prometheus_metrics_exposes_required_names():
    body = build_prometheus_metrics(FakeMetricsRepository()).decode("utf-8")

    assert "records_ingested_total" in body
    assert "preprocessing_pass_rate" in body
    assert "ingredient_resolution_rate" in body
    assert "validation_acceptance_rate" in body
    assert "pipeline_e2e_latency_p99" in body
    assert "dead_letter_rate" in body
    assert "llm_calls_per_batch" in body
