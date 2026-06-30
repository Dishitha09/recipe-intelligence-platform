from services.observability.metrics import PipelineMetricsRepository


def test_metrics_rate_handles_zero_denominator():
    repository = PipelineMetricsRepository()

    assert repository._rate(5, 0) == 0.0
    assert repository._rate(3, 4) == 0.75
