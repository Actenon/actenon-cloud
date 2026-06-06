from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from tests.integration.auth_helpers import create_operator_session


def create_tenant(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/tenants",
        json={"display_name": "Finance Approval Tenant", "finance_profile": "payments"},
    )
    assert response.status_code == 201
    return response.json()


def create_active_approval_policy(
    client: TestClient,
    tenant_id: str,
    *,
    eligible_principal_ids: list[str] | None = None,
    expires_in_seconds: int = 300,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant_id,
            "name": "High Value Approval Policy",
            "description": "Finance dual-control workflow",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [
                {
                    "rule_id": "dual-control-high-value",
                    "priority": 10,
                    "decision": "approval_required",
                    "approval_requirement": {
                        "required_decision_count": 1,
                        "eligible_principal_ids": list(
                            eligible_principal_ids or ["approver-001"]
                        ),
                        "expires_in_seconds": expires_in_seconds,
                        "require_requester_separation": True,
                        "require_distinct_approvers": True,
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
        "submission_id": "approval-submission-001",
        "idempotency_key": "approval-idempotency-key-0001",
        "requested_by": {"principal_type": "user", "principal_id": "requester-001"},
        "kernel_contract_ref": {
            "contract_family": "action_intent",
            "version_ref": "open_execution_kernel.action_intent.finance.v1alpha1",
        },
        "kernel_action_intent": {
            "intent_id": "approval-intent-001",
            "workflow_key": "payments.standard",
            "action_type": "transfer",
            "amount_minor": 700000,
            "currency": "USD",
            "source_account_ref": "acct-source-001",
            "destination_account_ref": "acct-destination-001",
            "destination_country": "GB",
            "evidence_refs": [],
        },
        "evaluation_context": {"risk_tier": "medium", "evidence_present": False},
        "client_tags": ["finance", "approvals"],
    }
    payload.update(overrides)
    return payload


def test_approval_request_creation_and_separation_of_duties(client: TestClient) -> None:
    tenant = create_tenant(client)
    requester = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="requester-001@example.com",
        display_name="Requester 001",
    )
    approver = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="approver-001@example.com",
        display_name="Approver 001",
    )
    create_active_approval_policy(
        client,
        tenant["tenant_id"],
        eligible_principal_ids=[approver["user"]["user_id"]],
    )

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            requested_by={
                "principal_type": "user",
                "principal_id": requester["user"]["user_id"],
            },
        ),
    )

    assert intake_response.status_code == 201
    intake_body = intake_response.json()
    assert intake_body["decision_state"] == "approval_required"
    assert intake_body["approval_state"] == "pending"

    approvals_response = client.get(
        "/api/v1/approvals",
        params={"action_intent_record_id": intake_body["action_intent_record_id"]},
    )
    assert approvals_response.status_code == 200
    approval_request = approvals_response.json()[0]
    assert approval_request["status"] == "pending"
    assert approval_request["assignments"][0]["principal_id"] == approver["user"]["user_id"]

    requester_decision = client.post(
        f"/api/v1/approvals/{approval_request['approval_request_id']}/decisions",
        headers=requester["headers"],
        json={
            "decision": "approve",
            "decision_reason": "self approval should fail",
            "principal_type": "user",
            "principal_id": approver["user"]["user_id"],
        },
    )
    assert requester_decision.status_code == 403

    approver_decision = client.post(
        f"/api/v1/approvals/{approval_request['approval_request_id']}/decisions",
        headers=approver["headers"],
        json={
            "decision": "approve",
            "decision_reason": "dual control satisfied",
            "principal_type": "user",
            "principal_id": requester["user"]["user_id"],
        },
    )
    assert approver_decision.status_code == 201
    assert approver_decision.json()["status"] == "satisfied"
    assert (
        approver_decision.json()["decisions"][0]["decided_by_principal_id"]
        == approver["user"]["user_id"]
    )

    refreshed_intent = client.get(
        f"/api/v1/action-intents/{intake_body['action_intent_record_id']}"
    )
    assert refreshed_intent.status_code == 200
    assert refreshed_intent.json()["approval_state"] == "satisfied"


def test_approval_request_expiration_updates_action_intent_state(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_approval_policy(client, tenant["tenant_id"], expires_in_seconds=1)

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="approval-submission-002",
            idempotency_key="approval-idempotency-key-0002",
        ),
    )
    assert intake_response.status_code == 201
    action_intent_record_id = intake_response.json()["action_intent_record_id"]

    approvals_response = client.get(
        "/api/v1/approvals",
        params={"action_intent_record_id": action_intent_record_id},
    )
    approval_request_id = approvals_response.json()[0]["approval_request_id"]

    time.sleep(1.2)

    expired_request = client.get(f"/api/v1/approvals/{approval_request_id}")
    assert expired_request.status_code == 200
    assert expired_request.json()["status"] == "expired"

    refreshed_intent = client.get(f"/api/v1/action-intents/{action_intent_record_id}")
    assert refreshed_intent.status_code == 200
    assert refreshed_intent.json()["approval_state"] == "expired"
