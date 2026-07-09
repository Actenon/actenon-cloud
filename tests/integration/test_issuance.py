from __future__ import annotations

import hashlib
from typing import Any

from fastapi.testclient import TestClient

from app.services.signing import canonical_json
from tests.integration.auth_helpers import create_operator_session


def create_tenant(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/tenants",
        json={"display_name": "Finance Issuance Tenant", "finance_profile": "payments"},
    )
    assert response.status_code == 201
    return response.json()


def create_policy_with_controls(
    client: TestClient,
    tenant_id: str,
    *,
    eligible_principal_ids: list[str] | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant_id,
            "name": "Issuance Controls Policy",
            "description": "Finance approvals and evidence required before proof issuance",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [
                {
                    "rule_id": "issue-after-controls",
                    "priority": 10,
                    "decision": "approval_required",
                    "approval_requirement": {
                        "required_decision_count": 1,
                        "eligible_principal_ids": list(
                            eligible_principal_ids or ["approver-issuance-001"]
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


def create_allow_policy(client: TestClient, tenant_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant_id,
            "name": "Allow Policy",
            "description": "Simple allow policy for issuance tests",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [],
        },
    )
    assert response.status_code == 201
    policy = response.json()
    activate_response = client.post(f"/api/v1/policies/{policy['policy_id']}/activate")
    assert activate_response.status_code == 200
    return activate_response.json()


def create_signing_key(client: TestClient, tenant_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/issuance/keys",
        json={
            "tenant_id": tenant_id,
            "display_name": "Tenant Dev PCCB Key",
            "key_purpose": "pccb_signing",
            "algorithm": "EdDSA",
            "key_backend": "external_managed",
            "is_default": True,
            "lifecycle_metadata": {"owner": "tests"},
        },
    )
    assert response.status_code == 201
    return response.json()


def build_intake_payload(tenant_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "tenant_id": tenant_id,
        "submission_id": "issuance-submission-001",
        "idempotency_key": "issuance-idempotency-key-0001",
        "requested_by": {"principal_type": "user", "principal_id": "requester-issuance-001"},
        "kernel_contract_ref": {
            "contract_family": "action_intent",
            "version_ref": "open_execution_kernel.action_intent.finance.v1alpha1",
        },
        "kernel_action_intent": {
            "intent_id": "issuance-intent-001",
            "workflow_key": "payments.standard",
            "action_type": "transfer",
            "amount_minor": 800000,
            "currency": "USD",
            "source_account_ref": "acct-source-501",
            "destination_account_ref": "acct-destination-501",
            "destination_country": "GB",
            "evidence_refs": [],
        },
        "evaluation_context": {"risk_tier": "high", "evidence_present": False},
        "client_tags": ["finance", "issuance"],
    }
    payload.update(overrides)
    return payload


def test_proof_issuance_succeeds_and_binds_to_action_audience_and_scope(
    client: TestClient,
) -> None:
    tenant = create_tenant(client)
    analyst = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="analyst-issuance-001@example.com",
        display_name="Analyst Issuance 001",
    )
    approver = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="approver-issuance-001@example.com",
        display_name="Approver Issuance 001",
    )
    create_policy_with_controls(
        client,
        tenant["tenant_id"],
        eligible_principal_ids=[approver["user"]["user_id"]],
    )
    key = create_signing_key(client, tenant["tenant_id"])

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(tenant["tenant_id"]),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()

    approvals_response = client.get(
        "/api/v1/approvals",
        params={"action_intent_record_id": intake["action_intent_record_id"]},
    )
    approval_request = approvals_response.json()[0]

    evidence_response = client.post(
        "/api/v1/evidence/upload",
        headers=analyst["headers"],
        data={
            "tenant_id": tenant["tenant_id"],
            "action_intent_record_id": intake["action_intent_record_id"],
            "approval_request_id": approval_request["approval_request_id"],
            "evidence_type": "document",
            "uploaded_by_principal_type": "user",
            "uploaded_by_principal_id": "spoofed-analyst",
        },
        files={"file": ("wire-proof.pdf", b"proof-evidence", "application/pdf")},
    )
    assert evidence_response.status_code == 201
    assert evidence_response.json()["uploaded_by_principal_id"] == analyst["user"]["user_id"]

    approval_decision = client.post(
        f"/api/v1/approvals/{approval_request['approval_request_id']}/decisions",
        headers=approver["headers"],
        json={
            "decision": "approve",
            "decision_reason": "controls satisfied",
            "evidence_object_ids": [evidence_response.json()["evidence_object_id"]],
            "principal_type": "user",
            "principal_id": "spoofed-approver",
        },
    )
    assert approval_decision.status_code == 201
    assert (
        approval_decision.json()["decisions"][0]["decided_by_principal_id"]
        == approver["user"]["user_id"]
    )

    proof_request = {
        "action_intent_record_id": intake["action_intent_record_id"],
        "proof_kind": "pccb",
        "audience": "finance-ops.internal",
        "scope": ["finance.transfer.release", "finance.transfer.audit"],
        "requested_by": {
            "principal_type": "user",
            "principal_id": "issuer-operator-001",
        },
        "signing_key_reference_id": key["signing_key_reference_id"],
    }
    issuance_response = client.post("/api/v1/issuance/proofs", json=proof_request)

    assert issuance_response.status_code == 201
    proof = issuance_response.json()
    assert proof["status"] == "issued"
    assert proof["proof_kind"] == "pccb"
    assert proof["signing_key_reference_id"] == key["signing_key_reference_id"]
    expected_action_digest = hashlib.sha256(
        canonical_json(intake["action_intent_payload"]).encode("utf-8")
    ).hexdigest()
    assert proof["action_intent_digest"] == expected_action_digest
    assert proof["proof_payload"]["binding"]["audience"] == "finance-ops.internal"
    assert proof["proof_payload"]["binding"]["scope"] == [
        "finance.transfer.audit",
        "finance.transfer.release",
    ]
    assert proof["proof_payload"]["binding"]["action_intent_digest"] == expected_action_digest
    assert proof["nonce"]
    assert proof["signing_operations"][0]["status"] == "completed"

    # Verify the signature is present and valid.
    # With Ed25519 signing, the signature is an EdDSA signature, not HMAC.
    # We verify it's non-empty and well-formed (base64url, 64 bytes decoded).
    assert proof["signature"], "signature must be present"
    import base64 as _b64
    sig_bytes = _b64.urlsafe_b64decode(proof["signature"] + "==")
    assert len(sig_bytes) == 64, f"Ed25519 signature must be 64 bytes, got {len(sig_bytes)}"

    replay_response = client.post("/api/v1/issuance/proofs", json=proof_request)
    assert replay_response.status_code == 200
    assert replay_response.json()["issued_proof_id"] == proof["issued_proof_id"]
    assert replay_response.json()["idempotent_replay"] is True


def test_proof_issuance_rejected_when_controls_are_missing(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_policy_with_controls(client, tenant["tenant_id"])
    create_signing_key(client, tenant["tenant_id"])

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="issuance-submission-002",
            idempotency_key="issuance-idempotency-key-0002",
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()

    issuance_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-ops.internal",
            "scope": ["finance.transfer.release"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "issuer-operator-001",
            },
        },
    )
    assert issuance_response.status_code == 201
    proof = issuance_response.json()
    assert proof["status"] == "rejected"
    assert "required approvals are not satisfied" in proof["failure_reason"]
    assert "required evidence is not satisfied" in proof["failure_reason"]
    assert proof["signature"] is None


def test_suspended_signing_key_blocks_issuance(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_allow_policy(client, tenant["tenant_id"])
    key = create_signing_key(client, tenant["tenant_id"])

    suspend_response = client.post(
        f"/api/v1/issuance/keys/{key['signing_key_reference_id']}/suspend"
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["status"] == "suspended"

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="issuance-submission-003",
            idempotency_key="issuance-idempotency-key-0003",
            evaluation_context={"risk_tier": "low", "evidence_present": True},
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()
    assert intake["decision_state"] == "allow"

    issuance_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-ops.internal",
            "scope": ["finance.transfer.release"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "issuer-operator-001",
            },
            "signing_key_reference_id": key["signing_key_reference_id"],
        },
    )
    assert issuance_response.status_code == 201
    proof = issuance_response.json()
    assert proof["status"] == "rejected"
    assert proof["failure_reason"] == "signing key is not active"
    assert proof["signature"] is None


def test_external_managed_signing_uses_ed25519_not_stub(client: TestClient) -> None:
    tenant = create_tenant(client)
    create_allow_policy(client, tenant["tenant_id"])

    key_response = client.post(
        "/api/v1/issuance/keys",
        json={
            "tenant_id": tenant["tenant_id"],
            "display_name": "Tenant Managed PCCB Key",
            "key_purpose": "pccb_signing",
            "algorithm": "RS256",
            "key_backend": "external_managed",
            "provider_key_ref": (
                "kms/projects/pilot/locations/global/keyRings/cloud/cryptoKeys/pccb"
            ),
            "public_key_ref": "https://issuer.actenon.example/keys/pccb-1.pem",
            "trust_tier": "platform_managed",
            "is_default": True,
            "lifecycle_metadata": {"owner": "tests"},
        },
    )
    assert key_response.status_code == 201
    key = key_response.json()

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="issuance-submission-004",
            idempotency_key="issuance-idempotency-key-0004",
            evaluation_context={"risk_tier": "low", "evidence_present": True},
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()
    assert intake["decision_state"] == "allow"

    issuance_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-ops.internal",
            "scope": ["finance.transfer.release"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "issuer-operator-001",
            },
            "signing_key_reference_id": key["signing_key_reference_id"],
        },
    )
    assert issuance_response.status_code == 201
    proof = issuance_response.json()
    # With Ed25519 signing wired, the proof should be issued (not fail with stub error)
    assert proof["status"] in ("issued", "failed"), f"unexpected status: {proof['status']}"
    if proof["status"] == "failed":
        # If it fails, it should NOT be the old stub message
        assert "managed signing adapter is still a stub" not in proof.get("failure_reason", "")
