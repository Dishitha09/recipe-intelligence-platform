from services.observability.metrics import PipelineMetricsRepository


PROMETHEUS_METRICS = {
    "records_ingested_total": "Total recipes currently stored.",
    "preprocessing_pass_rate": "Share of found records coerced successfully.",
    "ingredient_resolution_rate": "Share of ingredients with canonical names.",
    "validation_acceptance_rate": "Share of validation reports accepted.",
    "pipeline_e2e_latency_p99": "P99 ingestion run latency in seconds.",
    "dead_letter_rate": "Share of records ending in dead-letter storage.",
    "llm_calls_per_batch": "Average LLM calls per completed ingestion batch.",
}


def build_prometheus_metrics(repository=None):
    repository = repository or PipelineMetricsRepository()
    snapshot = repository.snapshot()

    try:
        from prometheus_client import CollectorRegistry, Gauge, generate_latest
    except ImportError:
        return _manual_prometheus(snapshot)

    registry = CollectorRegistry()

    for metric_name, description in PROMETHEUS_METRICS.items():
        gauge = Gauge(metric_name, description, registry=registry)
        gauge.set(float(snapshot.get(metric_name, 0) or 0))

    return generate_latest(registry)


def _manual_prometheus(snapshot):
    lines = []

    for metric_name, description in PROMETHEUS_METRICS.items():
        lines.append(f"# HELP {metric_name} {description}")
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {float(snapshot.get(metric_name, 0) or 0)}")

    return ("\n".join(lines) + "\n").encode("utf-8")
