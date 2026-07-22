from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.integration.auth_helpers import create_operator_session
from tests.integration.test_issuance import build_intake_payload, create_policy_with_controls


def _create_tenant(client: TestClient, display_name: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/tenants",
        json={"display_name": display_name, "finance_profile": "payments"},
    )
    assert response.status_code == 201
    return response.json()


def _create_action_with_controls(
    client: TestClient,
    *,
    tenant_id: str,
    suffix: str,
) -> dict[str, Any]:
    create_policy_with_controls(
        client,
        tenant_id,
        eligible_principal_ids=[f"approver-{suffix}"],
    )
    response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant_id,
            submission_id=f"isolation-submission-{suffix}",
            idempotency_key=f"isolation-idempotency-{suffix}",
            kernel_action_intent={
                "intent_id": f"isolation-intent-{suffix}",
                "workflow_key": "payments.standard",
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
                "source_account_ref": f"acct-source-{suffix}",
                "destination_account_ref": f"acct-destination-{suffix}",
                "destination_country": "GB",
                "evidence_refs": [],
            },
            evaluation_context={"risk_tier": "high", "evidence_present": False},
        ),
    )
    assert response.status_code == 201
    action = response.json()
    assert action["decision_state"] == "approval_required"
    return action


def _first_approval_for_action(client: TestClient, action_id: str) -> dict[str, Any]:
    response = client.get("/api/v1/approvals", params={"action_intent_record_id": action_id})
    assert response.status_code == 200
    approvals = response.json()
    assert len(approvals) == 1
    return approvals[0]


def _create_evidence(
    client: TestClient,
    *,
    tenant_id: str,
    action_id: str,
    approval_id: str,
    suffix: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/evidence/register",
        json={
            "tenant_id": tenant_id,
            "action_intent_record_id": action_id,
            "approval_request_id": approval_id,
            "evidence_type": "document",
            "storage_mode": "external_uri",
            "storage_ref": f"https://evidence.example/{suffix}/wire-proof.pdf",
            "original_filename": f"wire-proof-{suffix}.pdf",
            "media_type": "application/pdf",
            "content_digest": f"{suffix:0<64}"[:64],
            "size_bytes": 128,
            "evidence_metadata": {"tenant_marker": suffix},
        },
    )
    assert response.status_code == 201
    return response.json()


def _ingest_receipt(
    client: TestClient,
    *,
    tenant_id: str,
    action: dict[str, Any],
    suffix: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/receipts",
        json={
            "tenant_id": tenant_id,
            "action_intent_record_id": action["action_intent_record_id"],
            "kernel_contract_ref": {
                "contract_family": "receipt",
                "version_ref": "open_execution_kernel.receipt.finance.v1alpha1",
            },
            "kernel_receipt": {
                "receipt_id": f"isolation-receipt-{suffix}",
                "intent_id": action["external_action_intent_id"],
                "receipt_type": "execution_result",
                "outcome": "succeeded",
                "occurred_at": "2026-04-10T12:00:00Z",
                "action_intent_digest": action["action_intent_digest"],
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
                "source_account_ref": f"acct-source-{suffix}",
                "destination_account_ref": f"acct-destination-{suffix}",
                "provider_execution_ref": f"provider-exec-{suffix}",
            },
            "received_by": {"principal_type": "system", "principal_id": f"ingestor-{suffix}"},
        },
    )
    assert response.status_code == 201
    return response.json()


def _first_audit_event_for_tenant(client: TestClient, tenant_id: str) -> dict[str, Any]:
    response = client.get("/api/v1/audit/events", params={"tenant_id": tenant_id})
    assert response.status_code == 200
    events = response.json()
    assert events
    return events[0]


def _setup_two_tenant_fixture(client: TestClient) -> dict[str, dict[str, Any]]:
    tenant_a = _create_tenant(client, "Tenant Isolation A")
    tenant_b = _create_tenant(client, "Tenant Isolation B")
    action_a = _create_action_with_controls(client, tenant_id=tenant_a["tenant_id"], suffix="a")
    action_b = _create_action_with_controls(client, tenant_id=tenant_b["tenant_id"], suffix="b")
    approval_a = _first_approval_for_action(client, action_a["action_intent_record_id"])
    approval_b = _first_approval_for_action(client, action_b["action_intent_record_id"])
    evidence_a = _create_evidence(
        client,
        tenant_id=tenant_a["tenant_id"],
        action_id=action_a["action_intent_record_id"],
        approval_id=approval_a["approval_request_id"],
        suffix="a",
    )
    evidence_b = _create_evidence(
        client,
        tenant_id=tenant_b["tenant_id"],
        action_id=action_b["action_intent_record_id"],
        approval_id=approval_b["approval_request_id"],
        suffix="b",
    )
    receipt_a = _ingest_receipt(
        client,
        tenant_id=tenant_a["tenant_id"],
        action=action_a,
        suffix="a",
    )
    receipt_b = _ingest_receipt(
        client,
        tenant_id=tenant_b["tenant_id"],
        action=action_b,
        suffix="b",
    )
    audit_a = _first_audit_event_for_tenant(client, tenant_a["tenant_id"])
    audit_b = _first_audit_event_for_tenant(client, tenant_b["tenant_id"])
    operator_a = create_operator_session(
        client,
        tenant_id=tenant_a["tenant_id"],
        role_name="tenant_admin",
        email="tenant-isolation-a@example.com",
        display_name="Tenant Isolation A",
    )
    operator_b = create_operator_session(
        client,
        tenant_id=tenant_b["tenant_id"],
        role_name="tenant_admin",
        email="tenant-isolation-b@example.com",
        display_name="Tenant Isolation B",
    )
    orphan_operator = create_operator_session(
        client,
        email="tenant-isolation-orphan@example.com",
        display_name="Tenant Isolation Orphan",
    )
    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "action_a": action_a,
        "action_b": action_b,
        "approval_a": approval_a,
        "approval_b": approval_b,
        "evidence_a": evidence_a,
        "evidence_b": evidence_b,
        "receipt_a": receipt_a,
        "receipt_b": receipt_b,
        "audit_a": audit_a,
        "audit_b": audit_b,
        "operator_a": operator_a,
        "operator_b": operator_b,
        "orphan_operator": orphan_operator,
    }


def _ids(items: list[dict[str, Any]], field: str) -> set[str]:
    return {str(item[field]) for item in items}


def test_tenant_operator_cannot_read_or_mutate_another_tenant_surface(
    client: TestClient,
) -> None:
    fixture = _setup_two_tenant_fixture(client)
    tenant_a_id = fixture["tenant_a"]["tenant_id"]
    tenant_b_id = fixture["tenant_b"]["tenant_id"]
    headers_a = fixture["operator_a"]["headers"]

    actions_a = client.get("/api/v1/action-intents", headers=headers_a)
    assert actions_a.status_code == 200
    assert _ids(actions_a.json(), "tenant_id") == {tenant_a_id}
    assert fixture["action_b"]["action_intent_record_id"] not in _ids(
        actions_a.json(),
        "action_intent_record_id",
    )

    assert (
        client.get(
            "/api/v1/action-intents",
            headers=headers_a,
            params={"tenant_id": tenant_b_id},
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/action-intents/{fixture['action_b']['action_intent_record_id']}",
            headers=headers_a,
        ).status_code
        == 403
    )

    evidence_a = client.get("/api/v1/evidence", headers=headers_a)
    assert evidence_a.status_code == 200
    assert _ids(evidence_a.json(), "tenant_id") == {tenant_a_id}
    assert (
        client.get(
            f"/api/v1/evidence/{fixture['evidence_b']['evidence_object_id']}",
            headers=headers_a,
        ).status_code
        == 403
    )

    receipts_a = client.get("/api/v1/receipts", headers=headers_a)
    assert receipts_a.status_code == 200
    assert _ids(receipts_a.json(), "tenant_id") == {tenant_a_id}
    assert (
        client.get(
            f"/api/v1/receipts/{fixture['receipt_b']['receipt_id']}",
            headers=headers_a,
        ).status_code
        == 403
    )

    policies_a = client.get("/api/v1/policies", headers=headers_a)
    assert policies_a.status_code == 200
    assert _ids(policies_a.json(), "tenant_id") == {tenant_a_id}
    mutate_b_policy = client.put(
        f"/api/v1/policies/{fixture['action_b']['policy_id']}",
        headers=headers_a,
        json={
            "name": "Tenant B Policy Tamper",
            "description": "Tenant A must not be able to mutate this.",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [],
        },
    )
    assert mutate_b_policy.status_code == 403

    approvals_a = client.get("/api/v1/approvals", headers=headers_a)
    assert approvals_a.status_code == 200
    assert _ids(approvals_a.json(), "tenant_id") == {tenant_a_id}
    approve_b_action = client.post(
        f"/api/v1/approvals/{fixture['approval_b']['approval_request_id']}/decisions",
        headers=headers_a,
        json={
            "decision": "approve",
            "decision_reason": "cross-tenant approval attempt",
            "evidence_object_ids": [],
        },
    )
    assert approve_b_action.status_code == 403

    audit_events_a = client.get("/api/v1/audit/events", headers=headers_a)
    assert audit_events_a.status_code == 200
    assert _ids(audit_events_a.json(), "tenant_id") == {tenant_a_id}
    assert (
        client.get(
            f"/api/v1/audit/events/{fixture['audit_b']['audit_event_id']}",
            headers=headers_a,
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/audit/traces/{fixture['action_b']['action_intent_record_id']}",
            headers=headers_a,
        ).status_code
        == 403
    )

    usage_a = client.get("/api/v1/usage/summary", headers=headers_a)
    assert usage_a.status_code == 200
    assert usage_a.json()["tenant_id"] == tenant_a_id
    assert (
        client.get(
            "/api/v1/usage/summary",
            headers=headers_a,
            params={"tenant_id": tenant_b_id},
        ).status_code
        == 403
    )


def test_forged_or_missing_tenant_context_fails_closed(client: TestClient) -> None:
    fixture = _setup_two_tenant_fixture(client)
    tenant_a_id = fixture["tenant_a"]["tenant_id"]
    tenant_b_id = fixture["tenant_b"]["tenant_id"]
    headers_a = fixture["operator_a"]["headers"]
    orphan_headers = fixture["orphan_operator"]["headers"]

    forged_action = client.post(
        "/api/v1/action-intents",
        headers=headers_a,
        json=build_intake_payload(
            tenant_b_id,
            submission_id="forged-submission-b",
            idempotency_key="forged-idempotency-b",
        ),
    )
    assert forged_action.status_code == 403

    cross_tenant_evidence_reference = client.post(
        "/api/v1/evidence/register",
        headers=headers_a,
        json={
            "tenant_id": tenant_a_id,
            "action_intent_record_id": fixture["action_b"]["action_intent_record_id"],
            "approval_request_id": None,
            "evidence_type": "document",
            "storage_mode": "external_uri",
            "storage_ref": "https://evidence.example/cross-tenant.pdf",
        },
    )
    assert cross_tenant_evidence_reference.status_code == 400
    assert "does not belong to the requested tenant" in cross_tenant_evidence_reference.text

    cross_tenant_receipt_reference = client.post(
        "/api/v1/receipts",
        headers=headers_a,
        json={
            "tenant_id": tenant_a_id,
            "action_intent_record_id": fixture["action_b"]["action_intent_record_id"],
            "kernel_contract_ref": {
                "contract_family": "receipt",
                "version_ref": "open_execution_kernel.receipt.finance.v1alpha1",
            },
            "kernel_receipt": {
                "receipt_id": "cross-tenant-receipt",
                "intent_id": fixture["action_b"]["external_action_intent_id"],
                "receipt_type": "execution_result",
                "outcome": "succeeded",
                "occurred_at": "2026-04-10T13:00:00Z",
                "action_intent_digest": fixture["action_b"]["action_intent_digest"],
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
            },
            "received_by": {"principal_type": "system", "principal_id": "cross-tenant-ingestor"},
        },
    )
    assert cross_tenant_receipt_reference.status_code == 409

    forged_tenant_evidence = client.post(
        "/api/v1/evidence/register",
        headers=headers_a,
        json={
            "tenant_id": tenant_b_id,
            "action_intent_record_id": fixture["action_b"]["action_intent_record_id"],
            "approval_request_id": None,
            "evidence_type": "document",
            "storage_mode": "external_uri",
            "storage_ref": "https://evidence.example/forged-tenant.pdf",
        },
    )
    assert forged_tenant_evidence.status_code == 403

    forged_tenant_receipt = client.post(
        "/api/v1/receipts",
        headers=headers_a,
        json={
            "tenant_id": tenant_b_id,
            "action_intent_record_id": fixture["action_b"]["action_intent_record_id"],
            "kernel_contract_ref": {
                "contract_family": "receipt",
                "version_ref": "open_execution_kernel.receipt.finance.v1alpha1",
            },
            "kernel_receipt": {
                "receipt_id": "forged-tenant-receipt",
                "intent_id": fixture["action_b"]["external_action_intent_id"],
                "receipt_type": "execution_result",
                "outcome": "succeeded",
                "occurred_at": "2026-04-10T14:00:00Z",
                "action_intent_digest": fixture["action_b"]["action_intent_digest"],
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
            },
            "received_by": {"principal_type": "system", "principal_id": "forged-ingestor"},
        },
    )
    assert forged_tenant_receipt.status_code == 403

    assert client.get("/api/v1/action-intents", headers=orphan_headers).status_code == 403
    assert client.get("/api/v1/evidence", headers=orphan_headers).status_code == 403
    assert client.get("/api/v1/receipts", headers=orphan_headers).status_code == 403
    assert client.get("/api/v1/audit/events", headers=orphan_headers).status_code == 403
    assert client.get("/api/v1/usage/summary", headers=orphan_headers).status_code == 403
