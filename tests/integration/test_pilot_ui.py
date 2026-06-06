from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.test_action_intents import (
    build_intake_payload,
    create_active_policy,
    create_tenant,
)


def test_action_intent_list_endpoint_exposes_queue_fields(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_policy(client, tenant["tenant_id"])

    create_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            external_reference="invoice-queue-001",
        ),
    )
    assert create_response.status_code == 201

    list_response = client.get(
        "/api/v1/action-intents",
        params={
            "tenant_id": tenant["tenant_id"],
            "workflow_key": "payments.standard",
        },
    )

    assert list_response.status_code == 200
    body = list_response.json()
    assert len(body) == 1
    action = body[0]
    assert action["external_reference"] == "invoice-queue-001"
    assert action["amount_minor"] == 1000
    assert action["currency"] == "USD"
    assert action["source_account_ref"] == "acct-source-001"
    assert action["destination_account_ref"] == "acct-destination-001"
    assert action["decision_state"] == "allow"


def test_pilot_ui_pages_and_static_assets_are_served(client: TestClient) -> None:
    actions_page = client.get("/pilot/actions")
    assert actions_page.status_code == 200
    assert "Invoice Payment Actions" in actions_page.text
    assert "/pilot-static/actions-list.js" in actions_page.text

    review_page = client.get("/pilot/review")
    assert review_page.status_code == 200
    assert "Invoice Payment Review Queue" in review_page.text
    assert "/pilot-static/review-queue.js" in review_page.text

    detail_page = client.get("/pilot/actions/action-123")
    assert detail_page.status_code == 200
    assert "Invoice Payment Action Detail" in detail_page.text
    assert 'data-action-intent-record-id="action-123"' in detail_page.text

    style_asset = client.get("/pilot-static/pilot.css")
    assert style_asset.status_code == 200
    assert "pilot-shell" in style_asset.text

    actions_asset = client.get("/pilot-static/actions-list.js")
    assert actions_asset.status_code == 200
    assert "Current reporting period usage" in actions_asset.text
    assert "Metering only for the current pilot" in actions_asset.text
    assert "Proved and Allowed" in actions_asset.text
    assert "Reviewed" in actions_asset.text
    assert "Receipts Linked" in actions_asset.text
    assert "Invoice payment queue" in actions_asset.text
    assert "Supplier or payee" in actions_asset.text
    assert "Lifecycle" in actions_asset.text
    assert "Reviewability" in actions_asset.text
    assert "Artifacts" in actions_asset.text
    assert "Blocked / Refused" in actions_asset.text
    assert "Reviewable Now" in actions_asset.text
    assert "trace export in detail" in actions_asset.text
    assert "Updated" in actions_asset.text

    detail_asset = client.get("/pilot-static/action-detail.js")
    assert detail_asset.status_code == 200
    assert "Control outcome" in detail_asset.text
    assert "Lifecycle state" in detail_asset.text
    assert "Reviewability" in detail_asset.text
    assert "Receipt and export availability" in detail_asset.text
    assert "trace export ready" in detail_asset.text
    assert "Decision rationale" in detail_asset.text
    assert "Preview document" in detail_asset.text
    assert "Download document" in detail_asset.text
    assert "Open reference" in detail_asset.text
    assert "Lifecycle timeline" in detail_asset.text
    assert "Operator review" in detail_asset.text
    assert "Decline" in detail_asset.text
    assert "Request evidence" in detail_asset.text
    assert "Approval progression" in detail_asset.text
    assert "Proof progression" in detail_asset.text
    assert "Execution progression" in detail_asset.text
    assert "Current execution state" in detail_asset.text
    assert "Best recorded outcome" in detail_asset.text
    assert "Receipt progression" in detail_asset.text
    assert "Final recorded state" in detail_asset.text
    assert "What the operator can trust here" in detail_asset.text
    assert "Linked artifacts" in detail_asset.text

    review_asset = client.get("/pilot-static/review-queue.js")
    assert review_asset.status_code == 200
    assert "Invoice Payment Review Queue" in review_asset.text
    assert "Operator authority" in review_asset.text
    assert "approve, decline, request evidence, or export the trace" in review_asset.text
    assert "approval actions enabled" in review_asset.text
    assert "evidence actions enabled" in review_asset.text
    assert "Lifecycle" in review_asset.text
    assert "Reviewability" in review_asset.text
    assert "Artifacts" in review_asset.text
    assert "trace export in detail" in review_asset.text
    assert "Blocked final / refused" in review_asset.text
    assert "Manual follow-up" in review_asset.text
    assert (
        "does not persist operator notes, escalation ownership, or follow-up status"
        in review_asset.text
    )
