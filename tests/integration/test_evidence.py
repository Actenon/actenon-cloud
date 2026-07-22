from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from tests.integration.auth_helpers import create_operator_session


def create_tenant(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/tenants",
        json={"display_name": "Finance Evidence Tenant", "finance_profile": "payments"},
    )
    assert response.status_code == 201
    return response.json()


def create_active_evidence_policy(
    client: TestClient,
    tenant_id: str,
    *,
    eligible_principal_ids: list[str] | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant_id,
            "name": "Evidence Bound Approval Policy",
            "description": "Finance approval plus evidence workflow",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [
                {
                    "rule_id": "approval-with-evidence",
                    "priority": 10,
                    "decision": "approval_required",
                    "approval_requirement": {
                        "required_decision_count": 1,
                        "eligible_principal_ids": list(
                            eligible_principal_ids or ["approver-002"]
                        ),
                        "require_requester_separation": True,
                    },
                    "evidence_requirement": {
                        "minimum_count": 1,
                        "allowed_evidence_types": ["document"],
                    },
                    "all_conditions": [
                        {
                            "source": "action_intent",
                            "field": "amount_minor",
                            "operator": "gte",
                            "value": 500000,
                        }
                    ],
                }
            ],
        },
    )
    assert response.status_code == 201
    policy = response.json()
    activate_response = client.post(f"/api/v1/policies/{policy['policy_id']}/activate")
    assert activate_response.status_code == 200
    return activate_response.json()


def build_intake_payload(tenant_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "tenant_id": tenant_id,
        "submission_id": "evidence-submission-001",
        "idempotency_key": "evidence-idempotency-key-0001",
        "requested_by": {"principal_type": "user", "principal_id": "requester-002"},
        "kernel_contract_ref": {
            "contract_family": "action_intent",
            "version_ref": "open_execution_kernel.action_intent.finance.v1alpha1",
        },
        "kernel_action_intent": {
            "intent_id": "evidence-intent-001",
            "workflow_key": "payments.standard",
            "action_type": "transfer",
            "amount_minor": 900000,
            "currency": "USD",
            "source_account_ref": "acct-source-101",
            "destination_account_ref": "acct-destination-101",
            "destination_country": "GB",
            "evidence_refs": [],
        },
        "evaluation_context": {"risk_tier": "high", "evidence_present": False},
        "client_tags": ["finance", "evidence"],
    }
    payload.update(overrides)
    return payload


def test_evidence_registration_upload_and_approval_binding(client: TestClient) -> None:
    tenant = create_tenant(client)
    analyst = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="analyst-001@example.com",
        display_name="Analyst 001",
    )
    approver = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="approver-002@example.com",
        display_name="Approver 002",
    )
    create_active_evidence_policy(
        client,
        tenant["tenant_id"],
        eligible_principal_ids=[approver["user"]["user_id"]],
    )

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(tenant["tenant_id"]),
    )
    assert intake_response.status_code == 201
    intake_body = intake_response.json()
    assert intake_body["approval_state"] == "pending"
    assert intake_body["evidence_state"] == "pending"

    approvals_response = client.get(
        "/api/v1/approvals",
        params={"action_intent_record_id": intake_body["action_intent_record_id"]},
    )
    approval_request = approvals_response.json()[0]

    expired_evidence_response = client.post(
        "/api/v1/evidence/register",
        headers=analyst["headers"],
        json={
            "tenant_id": tenant["tenant_id"],
            "action_intent_record_id": intake_body["action_intent_record_id"],
            "approval_request_id": approval_request["approval_request_id"],
            "evidence_type": "document",
            "storage_mode": "external_uri",
            "storage_ref": "https://evidence.example/old-wire-proof.pdf",
            "original_filename": "old-wire-proof.pdf",
            "media_type": "application/pdf",
            "uploaded_by": {"principal_type": "user", "principal_id": "spoofed-analyst"},
            "evidence_metadata": {"source": "case-management"},
            "expires_at": "2000-01-01T00:00:00+00:00",
        },
    )
    assert expired_evidence_response.status_code == 201
    assert expired_evidence_response.json()["status"] == "expired"
    assert (
        expired_evidence_response.json()["uploaded_by_principal_id"]
        == analyst["user"]["user_id"]
    )

    expired_intent = client.get(f"/api/v1/action-intents/{intake_body['action_intent_record_id']}")
    assert expired_intent.status_code == 200
    assert expired_intent.json()["evidence_state"] == "expired"

    uploaded_evidence_response = client.post(
        "/api/v1/evidence/upload",
        headers=analyst["headers"],
        data={
            "tenant_id": tenant["tenant_id"],
            "action_intent_record_id": intake_body["action_intent_record_id"],
            "approval_request_id": approval_request["approval_request_id"],
            "evidence_type": "document",
            "uploaded_by_principal_type": "user",
            "uploaded_by_principal_id": "spoofed-analyst",
            "evidence_metadata_json": json.dumps({"source": "uploaded-manually"}),
        },
        files={"file": ("wire-proof.pdf", b"finance-evidence", "application/pdf")},
    )
    assert uploaded_evidence_response.status_code == 201
    uploaded_evidence = uploaded_evidence_response.json()
    assert uploaded_evidence["storage_mode"] == "filesystem"
    assert uploaded_evidence["status"] == "active"
    assert uploaded_evidence["content_digest"]
    assert uploaded_evidence["uploaded_by_principal_id"] == analyst["user"]["user_id"]

    evidence_content_response = client.get(
        f"/api/v1/evidence/{uploaded_evidence['evidence_object_id']}/content",
        params={"disposition": "attachment"},
    )
    assert evidence_content_response.status_code == 200
    assert evidence_content_response.content == b"finance-evidence"
    assert "attachment" in evidence_content_response.headers["content-disposition"]
    assert "wire-proof.pdf" in evidence_content_response.headers["content-disposition"]

    satisfied_evidence_intent = client.get(
        f"/api/v1/action-intents/{intake_body['action_intent_record_id']}"
    )
    assert satisfied_evidence_intent.status_code == 200
    assert satisfied_evidence_intent.json()["evidence_state"] == "satisfied"

    approval_decision_response = client.post(
        f"/api/v1/approvals/{approval_request['approval_request_id']}/decisions",
        headers=approver["headers"],
        json={
            "decision": "approve",
            "decision_reason": "evidence reviewed and approved",
            "evidence_object_ids": [uploaded_evidence["evidence_object_id"]],
            "principal_type": "user",
            "principal_id": "spoofed-approver",
        },
    )
    assert approval_decision_response.status_code == 201
    approval_request_body = approval_decision_response.json()
    assert approval_request_body["status"] == "satisfied"
    assert approval_request_body["decisions"][0]["evidence_object_ids"] == [
        uploaded_evidence["evidence_object_id"]
    ]
    assert (
        approval_request_body["decisions"][0]["decided_by_principal_id"]
        == approver["user"]["user_id"]
    )

    final_intent = client.get(f"/api/v1/action-intents/{intake_body['action_intent_record_id']}")
    assert final_intent.status_code == 200
    assert final_intent.json()["approval_state"] == "satisfied"
    assert final_intent.json()["evidence_state"] == "satisfied"


def test_external_evidence_content_download_is_not_available(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_evidence_policy(client, tenant["tenant_id"])
    analyst = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="analyst-002@example.com",
        display_name="Analyst 002",
    )

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(tenant["tenant_id"]),
    )
    assert intake_response.status_code == 201
    action_intent = intake_response.json()

    evidence_response = client.post(
        "/api/v1/evidence/register",
        headers=analyst["headers"],
        json={
            "tenant_id": tenant["tenant_id"],
            "action_intent_record_id": action_intent["action_intent_record_id"],
            "evidence_type": "external_reference",
            "storage_mode": "external_uri",
            "storage_ref": "https://evidence.example/reference",
            "uploaded_by": {"principal_type": "user", "principal_id": "spoofed-analyst"},
            "evidence_metadata": {"source": "vendor-portal"},
        },
    )
    assert evidence_response.status_code == 201
    evidence_object = evidence_response.json()
    assert evidence_object["uploaded_by_principal_id"] == analyst["user"]["user_id"]

    content_response = client.get(
        f"/api/v1/evidence/{evidence_object['evidence_object_id']}/content"
    )
    assert content_response.status_code == 409
    assert "not proxied for external URI evidence" in content_response.json()["detail"]


def test_object_store_evidence_content_download_is_not_available_without_backend_config(
    client: TestClient,
) -> None:
    tenant = create_tenant(client)
    create_active_evidence_policy(client, tenant["tenant_id"])
    analyst = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="analyst-003@example.com",
        display_name="Analyst 003",
    )

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(tenant["tenant_id"]),
    )
    assert intake_response.status_code == 201
    action_intent = intake_response.json()

    evidence_response = client.post(
        "/api/v1/evidence/register",
        headers=analyst["headers"],
        json={
            "tenant_id": tenant["tenant_id"],
            "action_intent_record_id": action_intent["action_intent_record_id"],
            "evidence_type": "document",
            "storage_mode": "object_store",
            "storage_ref": "pilot-evidence/invoice-payment/evidence-123",
            "original_filename": "wire-proof.pdf",
            "media_type": "application/pdf",
            "evidence_metadata": {"source": "preloaded-object-store"},
        },
    )
    assert evidence_response.status_code == 201
    evidence_object = evidence_response.json()

    content_response = client.get(
        f"/api/v1/evidence/{evidence_object['evidence_object_id']}/content"
    )
    assert content_response.status_code == 409
    assert "not configured for this deployment" in content_response.json()["detail"]
