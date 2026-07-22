from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_liveness_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_request_correlation_headers_are_propagated(client: TestClient) -> None:
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    response = client.get(
        "/api/v1/health/live",
        headers={
            "X-Request-ID": "request-123",
            "X-Correlation-ID": "correlation-456",
            "traceparent": f"00-{trace_id}-00f067aa0ba902b7-01",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"
    assert response.headers["X-Correlation-ID"] == "correlation-456"
    assert response.headers["X-Trace-ID"] == trace_id


def test_readiness_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    evidence_root = Path(client.app.state.container.settings.evidence_storage_root).resolve()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "action-control-plane",
        "environment": "test",
        "checks": {"database": "ready", "evidence_storage": "ready"},
        "details": {
            "database": "sqlite connection ok",
            "evidence_storage": f"writable directory available at {evidence_root}",
        },
    }


def test_readiness_endpoint_fails_when_evidence_storage_disappears(client: TestClient) -> None:
    evidence_root = Path(client.app.state.container.settings.evidence_storage_root)
    evidence_root.rmdir()

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "ready"
    assert body["checks"]["evidence_storage"] == "not_ready"
    assert "evidence storage unavailable" in body["details"]["evidence_storage"]


def test_metrics_endpoint_exposes_runtime_and_request_metrics(client: TestClient) -> None:
    client.get("/api/v1/health/live")
    client.get("/api/v1/health/ready")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert "action_control_plane_runtime_ready 1" in response.text
    assert 'action_control_plane_dependency_ready{check_name="database"} 1' in response.text
    assert (
        'action_control_plane_http_requests_total{method="GET",'
        'path_template="/api/v1/health/live",status_code="200"}'
    ) in response.text
    assert "action_control_plane_http_request_duration_seconds_bucket" in response.text
