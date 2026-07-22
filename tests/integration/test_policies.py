from __future__ import annotations

from fastapi.testclient import TestClient


def test_policy_management_flow(client: TestClient) -> None:
    tenant_response = client.post(
        "/api/v1/tenants",
        json={"display_name": "Finance Tenant", "finance_profile": "payments"},
    )
    assert tenant_response.status_code == 201
    tenant = tenant_response.json()

    create_response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant["tenant_id"],
            "name": "Payments Standard Policy",
            "description": "Finance workflow control policy",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [
                {
                    "rule_id": "high-value-approval",
                    "priority": 10,
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
    assert create_response.status_code == 201
    policy = create_response.json()
    assert policy["status"] == "draft"
    assert policy["version"] == 1

    list_response = client.get("/api/v1/policies", params={"tenant_id": tenant["tenant_id"]})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/api/v1/policies/{policy['policy_id']}",
        json={
            "name": "Payments Standard Policy",
            "description": "Updated finance workflow control policy",
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
                }
            ]
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated finance workflow control policy"

    activate_response = client.post(f"/api/v1/policies/{policy['policy_id']}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["status"] == "active"

    locked_update_response = client.put(
        f"/api/v1/policies/{policy['policy_id']}",
        json={
            "name": "Payments Standard Policy",
            "description": "Should not change",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": []
        },
    )
    assert locked_update_response.status_code == 409
