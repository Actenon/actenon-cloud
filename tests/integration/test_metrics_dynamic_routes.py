"""Tests that metrics path_template includes the /api/v1 prefix for dynamic
routes with path parameters, not just static routes like /api/v1/health/live.

Verifies:
  - /api/v1/action-intents/{action_intent_record_id} → full template in metrics
  - /api/v1/approvals/{approval_request_id}/decisions → full template in metrics
  - /api/v1/audit/traces/{action_intent_record_id} → full template in metrics
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_metrics_for_action_intents_detail_route(client: TestClient) -> None:
    """GET /api/v1/action-intents/{id} should produce a metrics entry with
    the full path template including /api/v1 prefix."""
    # First create an action intent to get a valid ID
    # (the route exists even if the ID is invalid — we just need the 404
    # to register a metric entry)
    client.get("/api/v1/action-intents/nonexistent-id")

    response = client.get("/metrics")
    assert response.status_code == 200
    # The path template should include the full /api/v1 prefix
    assert (
        'path_template="/api/v1/action-intents/{action_intent_record_id}"'
    ) in response.text, (
        "metrics must record the full path template with /api/v1 prefix for "
        "dynamic routes"
    )


def test_metrics_for_approvals_decisions_route(client: TestClient) -> None:
    """POST /api/v1/approvals/{id}/decisions should produce a metrics entry."""
    client.post("/api/v1/approvals/nonexistent-id/decisions", json={"decision": "approved"})

    response = client.get("/metrics")
    assert response.status_code == 200
    assert (
        'path_template="/api/v1/approvals/{approval_request_id}/decisions"'
    ) in response.text, (
        "metrics must record the full path template for approval decisions"
    )


def test_metrics_for_audit_traces_route(client: TestClient) -> None:
    """GET /api/v1/audit/traces/{id} should produce a metrics entry."""
    client.get("/api/v1/audit/traces/nonexistent-id")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert (
        'path_template="/api/v1/audit/traces/{action_intent_record_id}"'
    ) in response.text, (
        "metrics must record the full path template for audit traces"
    )


def test_all_dynamic_route_templates_have_api_v1_prefix(client: TestClient) -> None:
    """Every path_template in metrics for an API route must start with /api/v1."""
    # Hit a few routes to generate metrics
    client.get("/api/v1/health/live")
    client.get("/api/v1/action-intents/nonexistent")
    client.get("/api/v1/audit/traces/nonexistent")

    response = client.get("/metrics")
    assert response.status_code == 200

    for line in response.text.split("\n"):
        if "path_template=" not in line:
            continue
        if "action_control_plane_http_requests_total" not in line:
            continue
        # Extract the path_template value
        start = line.find('path_template="')
        if start == -1:
            continue
        start += len('path_template="')
        end = line.find('"', start)
        template = line[start:end]
        # Every API route template must include /api/v1
        # (except /metrics and /pilot-static which are not API routes)
        if template.startswith("/api/"):
            assert template.startswith("/api/v1/"), (
                f"path_template {template!r} must include /api/v1 prefix"
            )
