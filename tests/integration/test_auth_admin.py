from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.integration.test_receipts import create_governed_finance_trace


def create_tenant_with_name(client: TestClient, name: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/tenants",
        json={"display_name": name, "finance_profile": "payments"},
    )
    assert response.status_code == 201
    return response.json()


def get_tenant_role_id(client: TestClient, tenant_id: str, role_name: str) -> str:
    response = client.get("/api/v1/admin/roles", params={"tenant_id": tenant_id})
    assert response.status_code == 200
    for role in response.json():
        if role["scope"] == "tenant" and role["name"] == role_name:
            return role["role_id"]
    raise AssertionError(f"role '{role_name}' not found")


def create_operator_headers(
    client: TestClient,
    *,
    tenant_id: str,
    role_name: str,
    email: str,
    display_name: str,
) -> dict[str, str]:
    role_id = get_tenant_role_id(client, tenant_id, role_name)
    user_response = client.post(
        "/api/v1/admin/users",
        json={
            "email": email,
            "display_name": display_name,
            "platform_role_ids": [],
        },
    )
    assert user_response.status_code == 201
    user = user_response.json()

    membership_response = client.post(
        f"/api/v1/admin/tenants/{tenant_id}/memberships",
        json={"user_id": user["user_id"], "role_ids": [role_id]},
    )
    assert membership_response.status_code == 201

    token_response = client.post(
        "/api/v1/auth/dev/operator-token",
        json={"user_id": user["user_id"]},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_service_principal_headers(
    client: TestClient,
    *,
    tenant_id: str,
    role_name: str,
    display_name: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    role_id = get_tenant_role_id(client, tenant_id, role_name)
    principal_response = client.post(
        "/api/v1/admin/service-principals",
        json={
            "tenant_id": tenant_id,
            "display_name": display_name,
            "description": "Tenant scoped automation principal",
            "role_ids": [role_id],
        },
    )
    assert principal_response.status_code == 201
    principal = principal_response.json()

    token_response = client.post(
        "/api/v1/auth/dev/service-token",
        json={"service_principal_id": principal["service_principal_id"]},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, principal


def test_auth_session_exposes_platform_admin_context(client: TestClient) -> None:
    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    session = response.json()
    assert session["principal_type"] == "user"
    assert session["token_kind"] == "operator"  # noqa: S105
    assert "platform.admin.manage" in session["platform_permissions"]
    assert session["auth_mode"] == "development_signed_bearer"


def test_tenant_admin_is_limited_to_its_membership_tenant_for_policy_management(
    client: TestClient,
) -> None:
    tenant_a = create_tenant_with_name(client, "Tenant A")
    tenant_b = create_tenant_with_name(client, "Tenant B")
    tenant_admin_headers = create_operator_headers(
        client,
        tenant_id=tenant_a["tenant_id"],
        role_name="tenant_admin",
        email="tenant-admin-a@example.com",
        display_name="Tenant Admin A",
    )

    allowed_response = client.post(
        "/api/v1/policies",
        headers=tenant_admin_headers,
        json={
            "tenant_id": tenant_a["tenant_id"],
            "name": "Tenant A Policy",
            "description": "Tenant-scoped finance policy",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [],
        },
    )
    assert allowed_response.status_code == 201

    denied_response = client.post(
        "/api/v1/policies",
        headers=tenant_admin_headers,
        json={
            "tenant_id": tenant_b["tenant_id"],
            "name": "Tenant B Policy",
            "description": "Should be denied",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [],
        },
    )
    assert denied_response.status_code == 403

    tenant_visibility_response = client.get(
        f"/api/v1/tenants/{tenant_b['tenant_id']}",
        headers=tenant_admin_headers,
    )
    assert tenant_visibility_response.status_code == 403


def test_service_principal_receipt_access_is_scoped_to_its_tenant(client: TestClient) -> None:
    flow = create_governed_finance_trace(client)
    headers, principal = create_service_principal_headers(
        client,
        tenant_id=flow["tenant"]["tenant_id"],
        role_name="service_operator",
        display_name="receipt-ingestor-sp",
    )

    receipt_response = client.post(
        "/api/v1/receipts",
        headers=headers,
        json={
            "tenant_id": flow["tenant"]["tenant_id"],
            "action_intent_record_id": flow["intake"]["action_intent_record_id"],
            "issued_proof_id": flow["proof"]["issued_proof_id"],
            "escrow_record_id": flow["escrow"]["escrow_record_id"],
            "kernel_contract_ref": {
                "contract_family": "receipt",
                "version_ref": "open_execution_kernel.receipt.finance.v1alpha1",
            },
            "kernel_receipt": {
                "receipt_id": "service-receipt-001",
                "intent_id": flow["intake"]["external_action_intent_id"],
                "receipt_type": "execution_result",
                "outcome": "succeeded",
                "occurred_at": "2026-04-06T20:15:00Z",
                "action_intent_digest": flow["proof"]["action_intent_digest"],
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
                "source_account_ref": "acct-source-receipt-001",
                "destination_account_ref": "acct-destination-receipt-001",
                "provider_execution_ref": "provider-exec-service-001",
                "settlement_reference": "settlement-service-001",
                "proof_nonce": flow["proof"]["nonce"],
                "audience": flow["proof"]["audience"],
                "scope": flow["proof"]["scope"],
                "metadata": {"rail": "wire"},
            },
            "received_by": {
                "principal_type": "service_principal",
                "principal_id": principal["service_principal_id"],
            },
        },
    )
    assert receipt_response.status_code == 201

    same_tenant_list_response = client.get(
        "/api/v1/receipts",
        headers=headers,
        params={"tenant_id": flow["tenant"]["tenant_id"]},
    )
    assert same_tenant_list_response.status_code == 200
    assert len(same_tenant_list_response.json()) == 1

    other_tenant = create_tenant_with_name(client, "Other Tenant")
    cross_tenant_response = client.get(
        "/api/v1/receipts",
        headers=headers,
        params={"tenant_id": other_tenant["tenant_id"]},
    )
    assert cross_tenant_response.status_code == 403


def test_audit_trace_visibility_is_limited_to_authorized_tenant(client: TestClient) -> None:
    flow = create_governed_finance_trace(client)
    receipt_response = client.post(
        "/api/v1/receipts",
        json={
            "tenant_id": flow["tenant"]["tenant_id"],
            "action_intent_record_id": flow["intake"]["action_intent_record_id"],
            "issued_proof_id": flow["proof"]["issued_proof_id"],
            "escrow_record_id": flow["escrow"]["escrow_record_id"],
            "kernel_contract_ref": {
                "contract_family": "receipt",
                "version_ref": "open_execution_kernel.receipt.finance.v1alpha1",
            },
            "kernel_receipt": {
                "receipt_id": "audit-visibility-receipt-001",
                "intent_id": flow["intake"]["external_action_intent_id"],
                "receipt_type": "execution_result",
                "outcome": "succeeded",
                "occurred_at": "2026-04-06T20:25:00Z",
                "action_intent_digest": flow["proof"]["action_intent_digest"],
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
                "source_account_ref": "acct-source-receipt-001",
                "destination_account_ref": "acct-destination-receipt-001",
                "provider_execution_ref": "provider-exec-audit-001",
                "settlement_reference": "settlement-audit-001",
                "proof_nonce": flow["proof"]["nonce"],
                "audience": flow["proof"]["audience"],
                "scope": flow["proof"]["scope"],
                "metadata": {"rail": "wire"},
            },
            "received_by": {"principal_type": "system", "principal_id": "audit-ingestor-001"},
        },
    )
    assert receipt_response.status_code == 201

    same_tenant_headers = create_operator_headers(
        client,
        tenant_id=flow["tenant"]["tenant_id"],
        role_name="audit_viewer",
        email="audit-viewer@example.com",
        display_name="Audit Viewer",
    )
    other_tenant = create_tenant_with_name(client, "Audit Other Tenant")
    other_tenant_headers = create_operator_headers(
        client,
        tenant_id=other_tenant["tenant_id"],
        role_name="audit_viewer",
        email="audit-viewer-other@example.com",
        display_name="Audit Viewer Other",
    )

    allowed_trace = client.get(
        f"/api/v1/audit/traces/{flow['intake']['action_intent_record_id']}",
        headers=same_tenant_headers,
    )
    assert allowed_trace.status_code == 200

    denied_trace = client.get(
        f"/api/v1/audit/traces/{flow['intake']['action_intent_record_id']}",
        headers=other_tenant_headers,
    )
    assert denied_trace.status_code == 403
