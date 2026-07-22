from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.models import EscrowRecord
from tests.integration.test_issuance import (
    build_intake_payload,
    create_allow_policy,
    create_signing_key,
    create_tenant,
)


def create_issued_proof(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    tenant = create_tenant(client)
    create_allow_policy(client, tenant["tenant_id"])
    key = create_signing_key(client, tenant["tenant_id"])

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id=f"escrow-submission-{tenant['tenant_id']}",
            idempotency_key=f"escrow-idempotency-{tenant['tenant_id']}",
            kernel_action_intent={
                "intent_id": f"escrow-intent-{tenant['tenant_id']}",
                "workflow_key": "payments.standard",
                "action_type": "transfer",
                "amount_minor": 250000,
                "currency": "USD",
                "source_account_ref": "acct-source-escrow",
                "destination_account_ref": "acct-destination-escrow",
                "destination_country": "GB",
                "evidence_refs": [],
            },
            evaluation_context={"risk_tier": "medium", "evidence_present": False},
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()

    issuance_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-provider.internal",
            "scope": ["finance.transfer.release"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "issuer-escrow-001",
            },
            "signing_key_reference_id": key["signing_key_reference_id"],
        },
    )
    assert issuance_response.status_code == 201
    proof = issuance_response.json()
    assert proof["status"] == "issued"
    return intake, proof


def test_escrow_release_consume_and_execution_updates(client: TestClient) -> None:
    intake, proof = create_issued_proof(client)

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-manager-001"},
            "capability_metadata": {"rail": "wire", "region": "gb"},
        },
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()
    assert hold["status"] == "held"
    assert hold["execution_state"] == "capability_held"
    assert hold["audience"] == proof["audience"]
    assert hold["scope"] == proof["scope"]
    assert hold["action_intent_digest"] == proof["action_intent_digest"]
    assert hold["idempotent_replay"] is False

    replay_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-manager-001"},
        },
    )
    assert replay_response.status_code == 200
    assert replay_response.json()["escrow_record_id"] == hold["escrow_record_id"]
    assert replay_response.json()["idempotent_replay"] is True

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-manager-001"}
        },
    )
    assert release_response.status_code == 200
    released = release_response.json()
    assert released["status"] == "released"
    assert released["execution_state"] == "capability_released"
    assert released["capability_reference"]
    assert released["capability_token"]
    assert released["release_metadata"]["simulated"] is False
    assert released["release_metadata"]["binding"]["audience"] == proof["audience"]

    consume_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/consume",
        json={
            "capability_token": released["capability_token"],
            "consumed_by": {
                "principal_type": "service_principal",
                "principal_id": "payments-adapter-001",
            },
            "provider_execution_ref": "provider-exec-001",
            "provider_status": "accepted",
            "transition_metadata": {"dispatch_channel": "adapter-hook"},
        },
    )
    assert consume_response.status_code == 200
    consumed = consume_response.json()
    assert consumed["status"] == "consumed"
    assert consumed["execution_state"] == "dispatch_requested"
    assert consumed["provider_execution_ref"] == "provider-exec-001"

    dispatch_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/execution-updates",
        json={
            "observed_by": {
                "principal_type": "system",
                "principal_id": "provider-hook-observer",
            },
            "execution_state": "dispatch_confirmed",
            "provider_execution_ref": "provider-exec-001",
            "provider_status": "confirmed",
        },
    )
    assert dispatch_response.status_code == 200
    assert dispatch_response.json()["execution_state"] == "dispatch_confirmed"

    result_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/execution-updates",
        json={
            "observed_by": {
                "principal_type": "system",
                "principal_id": "provider-hook-observer",
            },
            "execution_state": "result_observed",
            "provider_execution_ref": "provider-exec-001",
            "provider_status": "settled",
            "transition_metadata": {"settlement_batch_id": "batch-001"},
        },
    )
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["status"] == "consumed"
    assert result["execution_state"] == "result_observed"
    assert [transition["transition_type"] for transition in result["transitions"]] == [
        "hold_created",
        "released",
        "consumed",
        "execution_update",
        "execution_update",
    ]

    action_intent_response = client.get(
        f"/api/v1/action-intents/{intake['action_intent_record_id']}"
    )
    assert action_intent_response.status_code == 200
    assert action_intent_response.json()["execution_state"] == "result_observed"


def test_escrow_revocation_blocks_future_consumption(client: TestClient) -> None:
    intake, proof = create_issued_proof(client)

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-manager-002"},
        },
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-manager-002"}
        },
    )
    assert release_response.status_code == 200

    revoke_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/revoke",
        json={
            "acted_by": {"principal_type": "user", "principal_id": "risk-officer-001"},
            "reason_code": "risk_override",
            "reason_detail": "Anomalous routing signal observed before dispatch",
        },
    )
    assert revoke_response.status_code == 200
    revoked = revoke_response.json()
    assert revoked["status"] == "revoked"
    assert revoked["execution_state"] == "revoked"
    assert revoked["revocation_reason_code"] == "risk_override"

    consume_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/consume",
        json={
            "capability_token": release_response.json()["capability_token"],
            "consumed_by": {
                "principal_type": "service_principal",
                "principal_id": "payments-adapter-002",
            },
        },
    )
    assert consume_response.status_code == 409
    assert "released escrow state" in consume_response.json()["detail"]

    action_intent_response = client.get(
        f"/api/v1/action-intents/{intake['action_intent_record_id']}"
    )
    assert action_intent_response.status_code == 200
    assert action_intent_response.json()["execution_state"] == "revoked"


def test_escrow_quarantine_freezes_execution_path(client: TestClient) -> None:
    intake, proof = create_issued_proof(client)

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-manager-003"},
        },
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-manager-003"}
        },
    )
    assert release_response.status_code == 200

    consume_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/consume",
        json={
            "capability_token": release_response.json()["capability_token"],
            "consumed_by": {
                "principal_type": "service_principal",
                "principal_id": "payments-adapter-003",
            },
            "provider_execution_ref": "provider-exec-003",
        },
    )
    assert consume_response.status_code == 200

    quarantine_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/quarantine",
        json={
            "acted_by": {"principal_type": "user", "principal_id": "risk-officer-002"},
            "reason_code": "post_dispatch_review",
            "reason_detail": "Execution requires manual review after dispatch request",
        },
    )
    assert quarantine_response.status_code == 200
    quarantined = quarantine_response.json()
    assert quarantined["status"] == "quarantined"
    assert quarantined["execution_state"] == "quarantined"
    assert quarantined["quarantine_reason_code"] == "post_dispatch_review"

    update_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/execution-updates",
        json={
            "observed_by": {
                "principal_type": "system",
                "principal_id": "provider-hook-observer",
            },
            "execution_state": "dispatch_confirmed",
        },
    )
    assert update_response.status_code == 409
    assert "consumed capability escrow record" in update_response.json()["detail"]

    action_intent_response = client.get(
        f"/api/v1/action-intents/{intake['action_intent_record_id']}"
    )
    assert action_intent_response.status_code == 200
    assert action_intent_response.json()["execution_state"] == "quarantined"


def test_escrow_expiry_refreshes_state_on_read(client: TestClient) -> None:
    intake, proof = create_issued_proof(client)

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-manager-004"},
            "expires_in_seconds": 60,
        },
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()

    with client.app.state.container.database.session() as session:
        record = session.get(EscrowRecord, hold["escrow_record_id"])
        assert record is not None
        record.expires_at = datetime.now(UTC) - timedelta(minutes=5)
        session.add(record)
        session.commit()

    refreshed_response = client.get(f"/api/v1/escrow/{hold['escrow_record_id']}")
    assert refreshed_response.status_code == 200
    refreshed = refreshed_response.json()
    assert refreshed["status"] == "expired"
    assert refreshed["execution_state"] == "expired"

    action_intent_response = client.get(
        f"/api/v1/action-intents/{intake['action_intent_record_id']}"
    )
    assert action_intent_response.status_code == 200
    assert action_intent_response.json()["execution_state"] == "expired"
