from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def get_tenant_role_id(client: TestClient, tenant_id: str, role_name: str) -> str:
    response = client.get("/api/v1/admin/roles", params={"tenant_id": tenant_id})
    assert response.status_code == 200
    for role in response.json():
        if role["scope"] == "tenant" and role["name"] == role_name:
            return role["role_id"]
    raise AssertionError(f"role '{role_name}' not found")


def create_operator_session(
    client: TestClient,
    *,
    email: str,
    display_name: str,
    tenant_id: str | None = None,
    role_name: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/admin/users",
        json={
            "email": email,
            "display_name": display_name,
            "platform_role_ids": [],
        },
    )
    assert response.status_code == 201
    user = response.json()

    if tenant_id is not None and role_name is not None:
        role_id = get_tenant_role_id(client, tenant_id, role_name)
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

    return {
        "user": user,
        "headers": {"Authorization": f"Bearer {token}"},
    }
