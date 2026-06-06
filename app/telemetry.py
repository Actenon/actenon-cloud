from __future__ import annotations

from dataclasses import asdict, dataclass

from app.config import Settings


@dataclass(frozen=True, slots=True)
class ObservabilityProfile:
    logging_backend: str
    metrics_backend: str
    tracing_backend: str
    health_model: str
    simulation_boundary: str

    def to_log_fields(self) -> dict[str, str]:
        return asdict(self)


def build_observability_profile(settings: Settings) -> ObservabilityProfile:
    logging_backend = "structured_json" if settings.log_format == "json" else "console"
    return ObservabilityProfile(
        logging_backend=logging_backend,
        metrics_backend="in_process_prometheus_text_endpoint",
        tracing_backend="request_and_correlation_headers_only",
        health_model="live=process ready=process_plus_database_plus_evidence_storage",
        simulation_boundary="no_distributed_tracing_exporter_no_alerting_pipeline",
    )
