from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.telemetry import build_observability_profile


def test_observability_profile_is_honest_about_current_runtime(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
        evidence_storage_root=str(tmp_path / "evidence"),
        log_format="json",
        enable_docs=False,
    )

    profile = build_observability_profile(settings)

    assert profile.logging_backend == "structured_json"
    assert profile.metrics_backend == "in_process_prometheus_text_endpoint"
    assert profile.tracing_backend == "request_and_correlation_headers_only"
    assert profile.health_model == "live=process ready=process_plus_database_plus_evidence_storage"
    assert profile.simulation_boundary == "no_distributed_tracing_exporter_no_alerting_pipeline"
