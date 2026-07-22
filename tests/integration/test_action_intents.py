from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def create_tenant(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/tenants",
        json={"display_name": "Finance Tenant", "finance_profile": "payments"},
    )
    assert response.status_code == 201
    return response.json()


def create_active_policy(client: TestClient, tenant_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant_id,
            "name": "Payments Workflow Policy",
            "description": "Finance workflow evaluation policy",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [
                {
                    "rule_id": "deny-country",
                    "priority": 5,
                    "decision": "deny",
                    "all_conditions": [
                        {
                            "source": "action_intent",
                            "field": "destination_country",
                            "operator": "in",
                            "value": ["KP", "IR"]
                        }
                    ]
                },
                {
                    "rule_id": "require-evidence-high-risk",
                    "priority": 10,
                    "decision": "needs_evidence",
                    "all_conditions": [
                        {
                            "source": "context",
                            "field": "risk_tier",
                            "operator": "in",
                            "value": ["high", "critical"]
                        },
                        {
                            "source": "context",
                            "field": "evidence_present",
                            "operator": "equals",
                            "value": False
                        }
                    ]
                },
                {
                    "rule_id": "approval-for-high-value",
                    "priority": 20,
                    "decision": "approval_required",
                    "all_conditions": [
                        {
                            "source": "action_intent",
                            "field": "amount_minor",
                            "operator": "gte",
                            "value": 500000
                        }
                    ]
                }
            ]
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
        "submission_id": "submission-001",
        "idempotency_key": "idempotency-key-0001",
        "requested_by": {"principal_type": "user", "principal_id": "user-001"},
        "kernel_contract_ref": {
            "contract_family": "action_intent",
            "version_ref": "open_execution_kernel.action_intent.finance.v1alpha1"
        },
        "kernel_action_intent": {
            "intent_id": "intent-001",
            "workflow_key": "payments.standard",
            "action_type": "transfer",
            "amount_minor": 1000,
            "currency": "USD",
            "source_account_ref": "acct-source-001",
            "destination_account_ref": "acct-destination-001",
            "destination_country": "GB",
            "evidence_refs": []
        },
        "evaluation_context": {"risk_tier": "low", "evidence_present": True},
        "client_tags": ["finance", "release-1"]
    }
    payload.update(overrides)
    return payload


def test_action_intent_allow_decision(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_policy(client, tenant["tenant_id"])

    response = client.post("/api/v1/action-intents", json=build_intake_payload(tenant["tenant_id"]))

    assert response.status_code == 201
    body = response.json()
    assert body["decision_state"] == "allow"
    assert body["contract_validation_status"] == "valid"


def test_action_intent_approval_required_decision(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_policy(client, tenant["tenant_id"])

    payload = build_intake_payload(
        tenant["tenant_id"],
        submission_id="submission-002",
        idempotency_key="idempotency-key-0002",
    )
    payload["kernel_action_intent"]["amount_minor"] = 700000

    response = client.post("/api/v1/action-intents", json=payload)

    assert response.status_code == 201
    assert response.json()["decision_state"] == "approval_required"


def test_action_intent_needs_evidence_decision(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_policy(client, tenant["tenant_id"])

    payload = build_intake_payload(
        tenant["tenant_id"],
        submission_id="submission-003",
        idempotency_key="idempotency-key-0003",
        evaluation_context={"risk_tier": "high", "evidence_present": False},
    )

    response = client.post("/api/v1/action-intents", json=payload)

    assert response.status_code == 201
    assert response.json()["decision_state"] == "needs_evidence"


def test_action_intent_deny_decision(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_policy(client, tenant["tenant_id"])

    payload = build_intake_payload(
        tenant["tenant_id"],
        submission_id="submission-004",
        idempotency_key="idempotency-key-0004",
    )
    payload["kernel_action_intent"]["destination_country"] = "KP"

    response = client.post("/api/v1/action-intents", json=payload)

    assert response.status_code == 201
    assert response.json()["decision_state"] == "deny"


def test_action_intent_structurally_non_executable_decision(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_policy(client, tenant["tenant_id"])

    payload = build_intake_payload(
        tenant["tenant_id"],
        submission_id="submission-005",
        idempotency_key="idempotency-key-0005",
    )
    payload["kernel_action_intent"]["destination_account_ref"] = "acct-source-001"

    response = client.post("/api/v1/action-intents", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision_state"] == "structurally_non_executable"
    assert body["contract_validation_status"] == "valid"


def test_action_intent_idempotency_replay_returns_existing_record(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_active_policy(client, tenant["tenant_id"])
    payload = build_intake_payload(tenant["tenant_id"])

    first_response = client.post("/api/v1/action-intents", json=payload)
    second_response = client.post("/api/v1/action-intents", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert (
        first_response.json()["action_intent_record_id"]
        == second_response.json()["action_intent_record_id"]
    )
    assert second_response.json()["idempotent_replay"] is True
