from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.integration.auth_helpers import create_operator_session
from tests.integration.test_issuance import (
    build_intake_payload,
    create_signing_key,
    create_tenant,
)


def create_usage_policy(
    client: TestClient,
    tenant_id: str,
    *,
    eligible_principal_ids: list[str],
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant_id,
            "name": "Usage Reporting Policy",
            "description": "Combines blocked, reviewed, and proved invoice-payment cases.",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [
                {
                    "rule_id": "deny-sanctioned-destination",
                    "priority": 5,
                    "decision": "deny",
                    "all_conditions": [
                        {
                            "source": "action_intent",
                            "field": "destination_country",
                            "operator": "in",
                            "value": ["KP"],
                        }
                    ],
                },
                {
                    "rule_id": "approve-high-value-with-evidence",
                    "priority": 10,
                    "decision": "approval_required",
                    "approval_requirement": {
                        "required_decision_count": 1,
                        "eligible_principal_ids": eligible_principal_ids,
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
                },
            ],
        },
    )
    assert response.status_code == 201
    policy = response.json()
    activate_response = client.post(f"/api/v1/policies/{policy['policy_id']}/activate")
    assert activate_response.status_code == 200
    return activate_response.json()


def test_usage_summary_separates_billable_candidates_from_blocked_value_signal(
    client: TestClient,
) -> None:
    tenant = create_tenant(client)
    analyst = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="usage-analyst-001@example.com",
        display_name="Usage Analyst 001",
    )
    approver = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="usage-approver-001@example.com",
        display_name="Usage Approver 001",
    )
    create_usage_policy(
        client,
        tenant["tenant_id"],
        eligible_principal_ids=[approver["user"]["user_id"]],
    )
    signing_key = create_signing_key(client, tenant["tenant_id"])

    allowed_payload = build_intake_payload(
        tenant["tenant_id"],
        submission_id="usage-submission-allow-001",
        idempotency_key="usage-idempotency-allow-0001",
    )
    allowed_payload["kernel_action_intent"]["amount_minor"] = 100000
    allowed_response = client.post("/api/v1/action-intents", json=allowed_payload)
    assert allowed_response.status_code == 201
    assert allowed_response.json()["decision_state"] == "allow"

    blocked_payload = build_intake_payload(
        tenant["tenant_id"],
        submission_id="usage-submission-blocked-001",
        idempotency_key="usage-idempotency-blocked-0001",
    )
    blocked_payload["kernel_action_intent"]["destination_country"] = "KP"
    blocked_response = client.post("/api/v1/action-intents", json=blocked_payload)
    assert blocked_response.status_code == 201
    assert blocked_response.json()["decision_state"] == "deny"

    metered_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="usage-submission-metered-001",
            idempotency_key="usage-idempotency-metered-0001",
            kernel_action_intent={
                "intent_id": "usage-metered-intent-001",
                "workflow_key": "payments.standard",
                "action_type": "transfer",
                "amount_minor": 850000,
                "currency": "USD",
                "source_account_ref": "acct-source-usage-001",
                "destination_account_ref": "acct-destination-usage-001",
                "destination_country": "GB",
                "evidence_refs": [],
            },
            evaluation_context={"risk_tier": "medium", "evidence_present": False},
        ),
    )
    assert metered_response.status_code == 201
    metered_action = metered_response.json()
    assert metered_action["decision_state"] == "approval_required"

    approvals_response = client.get(
        "/api/v1/approvals",
        params={"action_intent_record_id": metered_action["action_intent_record_id"]},
    )
    assert approvals_response.status_code == 200
    approval_request = approvals_response.json()[0]

    evidence_response = client.post(
        "/api/v1/evidence/upload",
        headers=analyst["headers"],
        data={
            "tenant_id": tenant["tenant_id"],
            "action_intent_record_id": metered_action["action_intent_record_id"],
            "approval_request_id": approval_request["approval_request_id"],
            "evidence_type": "document",
        },
        files={"file": ("usage-proof.pdf", b"usage-evidence", "application/pdf")},
    )
    assert evidence_response.status_code == 201
    evidence = evidence_response.json()

    decision_response = client.post(
        f"/api/v1/approvals/{approval_request['approval_request_id']}/decisions",
        headers=approver["headers"],
        json={
            "decision": "approve",
            "decision_reason": "usage controls satisfied",
            "evidence_object_ids": [evidence["evidence_object_id"]],
        },
    )
    assert decision_response.status_code == 201

    proof_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": metered_action["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-provider.internal",
            "scope": ["finance.transfer.release"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "usage-meter-issuer-001",
            },
            "signing_key_reference_id": signing_key["signing_key_reference_id"],
        },
    )
    assert proof_response.status_code == 201
    proof = proof_response.json()
    assert proof["status"] == "issued"

    receipt_response = client.post(
        "/api/v1/receipts",
        json={
            "tenant_id": tenant["tenant_id"],
            "action_intent_record_id": metered_action["action_intent_record_id"],
            "issued_proof_id": proof["issued_proof_id"],
            "kernel_contract_ref": {
                "contract_family": "receipt",
                "version_ref": "open_execution_kernel.receipt.finance.v1alpha1",
            },
            "kernel_receipt": {
                "receipt_id": "usage-receipt-001",
                "intent_id": metered_action["external_action_intent_id"],
                "receipt_type": "execution_result",
                "outcome": "succeeded",
                "occurred_at": "2026-04-09T12:00:00Z",
                "action_intent_digest": proof["action_intent_digest"],
                "action_type": "transfer",
                "amount_minor": 850000,
                "currency": "USD",
                "source_account_ref": "acct-source-usage-001",
                "destination_account_ref": "acct-destination-usage-001",
                "proof_nonce": proof["nonce"],
                "audience": proof["audience"],
                "scope": proof["scope"],
            },
            "received_by": {"principal_type": "system", "principal_id": "usage-receipt-ingestor"},
        },
    )
    assert receipt_response.status_code == 201

    summary_response = client.get(
        "/api/v1/usage/summary",
        params={
            "tenant_id": tenant["tenant_id"],
            "workflow_key": "payments.standard",
        },
    )
    assert summary_response.status_code == 200
    body = summary_response.json()

    assert body["tenant_id"] == tenant["tenant_id"]
    assert body["workflow_key"] == "payments.standard"
    assert body["totals"] == {
        "submitted_actions": 3,
        "billable_proved_and_allowed_actions": 1,
        "blocked_or_refused_actions": 1,
        "blocked_policy_actions": 1,
        "structurally_refused_actions": 0,
        "held_for_review_actions": 1,
        "reviewed_actions": 1,
        "receipt_linked_actions": 1,
    }
    assert body["definitions"]["pricing_status"] == "metering_only_no_invoicing"
    assert "not usage-billed" in body["definitions"]["blocked_action_definition"]
    assert len(body["daily_buckets"]) >= 1
    assert body["daily_buckets"][-1]["billable_proved_and_allowed_actions"] == 1


def test_usage_summary_requires_complete_custom_period_bounds(client: TestClient) -> None:
    tenant = create_tenant(client)

    response = client.get(
        "/api/v1/usage/summary",
        params={
            "tenant_id": tenant["tenant_id"],
            "period_start": "2026-04-01T00:00:00Z",
        },
    )

    assert response.status_code == 400
    assert "must be provided together" in response.json()["detail"]
