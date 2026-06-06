from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.integration.auth_helpers import create_operator_session
from tests.integration.test_escrow import create_issued_proof
from tests.integration.test_issuance import (
    build_intake_payload,
    create_policy_with_controls,
    create_signing_key,
    create_tenant,
)


def create_governed_finance_trace(client: TestClient) -> dict[str, Any]:
    tenant = create_tenant(client)
    analyst = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="analyst-receipt-001@example.com",
        display_name="Analyst Receipt 001",
    )
    approver = create_operator_session(
        client,
        tenant_id=tenant["tenant_id"],
        role_name="tenant_admin",
        email="approver-receipt-001@example.com",
        display_name="Approver Receipt 001",
    )
    create_policy_with_controls(
        client,
        tenant["tenant_id"],
        eligible_principal_ids=[approver["user"]["user_id"]],
    )
    key = create_signing_key(client, tenant["tenant_id"])

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="receipt-submission-001",
            idempotency_key="receipt-idempotency-key-0001",
            kernel_action_intent={
                "intent_id": "receipt-intent-001",
                "workflow_key": "payments.standard",
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
                "source_account_ref": "acct-source-receipt-001",
                "destination_account_ref": "acct-destination-receipt-001",
                "destination_country": "GB",
                "evidence_refs": [],
            },
            evaluation_context={"risk_tier": "high", "evidence_present": False},
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()

    approvals_response = client.get(
        "/api/v1/approvals",
        params={"action_intent_record_id": intake["action_intent_record_id"]},
    )
    assert approvals_response.status_code == 200
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
        files={"file": ("payment-proof.pdf", b"receipt-evidence", "application/pdf")},
    )
    assert evidence_response.status_code == 201
    evidence = evidence_response.json()
    assert evidence["uploaded_by_principal_id"] == analyst["user"]["user_id"]

    decision_response = client.post(
        f"/api/v1/approvals/{approval_request['approval_request_id']}/decisions",
        headers=approver["headers"],
        json={
            "decision": "approve",
            "decision_reason": "receipt controls satisfied",
            "evidence_object_ids": [evidence["evidence_object_id"]],
            "principal_type": "user",
            "principal_id": "spoofed-approver",
        },
    )
    assert decision_response.status_code == 201
    decision = decision_response.json()
    assert (
        decision["decisions"][0]["decided_by_principal_id"]
        == approver["user"]["user_id"]
    )

    issuance_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-provider.internal",
            "scope": ["finance.transfer.release", "finance.transfer.audit"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "issuer-receipt-001",
            },
            "signing_key_reference_id": key["signing_key_reference_id"],
        },
    )
    assert issuance_response.status_code == 201
    proof = issuance_response.json()

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-manager-101"},
            "capability_metadata": {"rail": "wire"},
        },
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-manager-101"}
        },
    )
    assert release_response.status_code == 200
    released = release_response.json()

    consume_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/consume",
        json={
            "capability_token": released["capability_token"],
            "consumed_by": {
                "principal_type": "service_principal",
                "principal_id": "payments-adapter-101",
            },
            "provider_execution_ref": "provider-exec-receipt-001",
            "provider_status": "accepted",
        },
    )
    assert consume_response.status_code == 200

    return {
        "tenant": tenant,
        "intake": intake,
        "approval_request": approval_request,
        "decision": decision,
        "evidence": evidence,
        "proof": proof,
        "escrow": consume_response.json(),
    }


def test_receipt_ingestion_links_full_finance_trace_and_exposes_audit_bundle(
    client: TestClient,
) -> None:
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
                "receipt_id": "kernel-receipt-001",
                "intent_id": flow["intake"]["external_action_intent_id"],
                "receipt_type": "execution_result",
                "outcome": "succeeded",
                "occurred_at": "2026-04-06T20:05:00Z",
                "action_intent_digest": flow["proof"]["action_intent_digest"],
                "action_type": "transfer",
                "amount_minor": 900000,
                "currency": "USD",
                "source_account_ref": "acct-source-receipt-001",
                "destination_account_ref": "acct-destination-receipt-001",
                "provider_execution_ref": "provider-exec-receipt-001",
                "settlement_reference": "settlement-001",
                "proof_nonce": flow["proof"]["nonce"],
                "audience": flow["proof"]["audience"],
                "scope": flow["proof"]["scope"],
                "metadata": {"rail": "wire"}
            },
            "received_by": {"principal_type": "system", "principal_id": "receipt-ingestor-001"},
        },
    )
    assert receipt_response.status_code == 201
    receipt = receipt_response.json()
    assert receipt["contract_validation_status"] == "valid"
    assert receipt["receipt_state"] == "reconciled"
    assert receipt["issued_proof_id"] == flow["proof"]["issued_proof_id"]
    assert receipt["escrow_record_id"] == flow["escrow"]["escrow_record_id"]
    assert flow["approval_request"]["approval_request_id"] in receipt["linked_approval_request_ids"]
    assert (
        flow["decision"]["decisions"][0]["approval_decision_id"]
        in receipt["linked_approval_decision_ids"]
    )
    assert flow["evidence"]["evidence_object_id"] in receipt["linked_evidence_object_ids"]
    assert receipt["reconciliation_summary"]["overall_status"] == "matched"

    query_response = client.get(
        "/api/v1/receipts",
        params={"provider_execution_ref": "provider-exec-receipt-001"},
    )
    assert query_response.status_code == 200
    assert len(query_response.json()) == 1
    assert query_response.json()[0]["receipt_id"] == receipt["receipt_id"]

    action_intent_response = client.get(
        f"/api/v1/action-intents/{flow['intake']['action_intent_record_id']}"
    )
    assert action_intent_response.status_code == 200
    action_intent = action_intent_response.json()
    assert action_intent["receipt_state"] == "reconciled"
    assert action_intent["latest_receipt_id"] == receipt["receipt_id"]
    assert action_intent["execution_state"] == "result_observed"

    trace_response = client.get(
        f"/api/v1/audit/traces/{flow['intake']['action_intent_record_id']}"
    )
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["summary"]["latest_receipt_id"] == receipt["receipt_id"]
    assert len(trace["approvals"]) == 1
    assert len(trace["approval_decisions"]) == 1
    assert len(trace["evidence_objects"]) == 1
    assert len(trace["issued_proofs"]) == 1
    assert len(trace["escrow_records"]) == 1
    assert len(trace["receipts"]) == 1
    assert len(trace["reconciliation_records"]) == 3
    assert len(trace["audit_events"]) >= 4

    export_response = client.get(
        "/api/v1/audit/export",
        params={"action_intent_record_id": flow["intake"]["action_intent_record_id"]},
    )
    assert export_response.status_code == 200
    assert export_response.json()["trace"]["summary"]["latest_receipt_id"] == receipt["receipt_id"]


def test_receipt_ingestion_flags_mismatched_proof_binding_and_is_idempotent(
    client: TestClient,
) -> None:
    intake, proof = create_issued_proof(client)

    receipt_request = {
        "tenant_id": intake["tenant_id"],
        "action_intent_record_id": intake["action_intent_record_id"],
        "issued_proof_id": proof["issued_proof_id"],
        "kernel_contract_ref": {
            "contract_family": "receipt",
            "version_ref": "open_execution_kernel.receipt.finance.v1alpha1",
        },
        "kernel_receipt": {
            "receipt_id": "kernel-receipt-mismatch-001",
            "intent_id": intake["external_action_intent_id"],
            "receipt_type": "failure_notice",
            "outcome": "failed",
            "occurred_at": "2026-04-06T21:10:00Z",
            "action_intent_digest": proof["action_intent_digest"],
            "action_type": "transfer",
            "amount_minor": 250000,
            "currency": "USD",
            "proof_nonce": "wrong-proof-nonce",
            "audience": "wrong-audience.internal",
            "scope": ["finance.transfer.release"]
        },
        "received_by": {"principal_type": "system", "principal_id": "receipt-ingestor-002"},
    }

    first_response = client.post("/api/v1/receipts", json=receipt_request)
    assert first_response.status_code == 201
    receipt = first_response.json()
    assert receipt["receipt_state"] == "indexed"
    assert receipt["reconciliation_summary"]["overall_status"] == "manual_review_required"

    replay_response = client.post("/api/v1/receipts", json=receipt_request)
    assert replay_response.status_code == 200
    assert replay_response.json()["receipt_id"] == receipt["receipt_id"]
    assert replay_response.json()["idempotent_replay"] is True

    reconciliation_response = client.get(
        "/api/v1/audit/reconciliation",
        params={"action_intent_record_id": intake["action_intent_record_id"]},
    )
    assert reconciliation_response.status_code == 200
    reconciliations = reconciliation_response.json()
    assert any(
        record["reconciliation_type"] == "proof_to_receipt" and record["status"] == "mismatch"
        for record in reconciliations
    )

    events_response = client.get(
        "/api/v1/audit/events",
        params={
            "action_intent_record_id": intake["action_intent_record_id"],
            "event_type": "reconciliation.proof_to_receipt.mismatch",
        },
    )
    assert events_response.status_code == 200
    assert len(events_response.json()) == 1

    action_intent_response = client.get(
        f"/api/v1/action-intents/{intake['action_intent_record_id']}"
    )
    assert action_intent_response.status_code == 200
    assert action_intent_response.json()["execution_state"] == "failure_observed"
