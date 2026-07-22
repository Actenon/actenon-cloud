from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    EscrowRecord,
    EscrowStatus,
    EscrowTransitionRecord,
    EscrowTransitionType,
    IssuedProof,
    ProofIssuanceStatus,
    ProofKind,
    SigningOperationRecord,
)
from app.services.approvals import ApprovalService
from app.services.escrow import EscrowActor, EscrowService, EscrowStateError
from app.services.evidence import EvidenceService
from app.services.issuance import IssuanceService, IssuerActor
from app.services.signing import SigningService
from tests.integration.test_escrow import create_issued_proof
from tests.integration.test_issuance import (
    build_intake_payload,
    create_allow_policy,
    create_signing_key,
    create_tenant,
)

THREAD_COUNT = 8


def _issuance_service(client: TestClient, session: Session) -> IssuanceService:
    settings = client.app.state.container.settings
    return IssuanceService(
        session,
        settings=settings,
        approval_service=ApprovalService(session),
        evidence_service=EvidenceService.from_settings(session, settings=settings),
        signing_service=SigningService(session, settings=settings),
    )


def _escrow_service(client: TestClient, session: Session) -> EscrowService:
    return EscrowService(
        session,
        settings=client.app.state.container.settings,
    )


def test_concurrent_proof_issuance_requests_return_single_issued_proof(
    client: TestClient,
) -> None:
    tenant = create_tenant(client)
    create_allow_policy(client, tenant["tenant_id"])
    key = create_signing_key(client, tenant["tenant_id"])
    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="atomicity-issuance-submission",
            idempotency_key="atomicity-issuance-idempotency",
            evaluation_context={"risk_tier": "low", "evidence_present": True},
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()
    barrier = threading.Barrier(THREAD_COUNT)

    def worker() -> tuple[str, bool, str]:
        with client.app.state.container.database.session() as session:
            service = _issuance_service(client, session)
            barrier.wait(timeout=10)
            result = service.issue_proof(
                action_intent_record_id=intake["action_intent_record_id"],
                proof_kind=ProofKind.pccb,
                audience="finance-provider.internal",
                scope=["finance.transfer.release"],
                expires_in_seconds=None,
                requested_by=IssuerActor(
                    principal_type="user",
                    principal_id="issuer-atomicity-001",
                ),
                signing_key_reference_id=key["signing_key_reference_id"],
            )
            return (
                result.proof.issued_proof_id,
                result.idempotent_replay,
                result.proof.status.value,
            )

    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        results = list(executor.map(lambda _: worker(), range(THREAD_COUNT)))

    proof_ids = [proof_id for proof_id, _, _ in results]
    replay_flags = [idempotent_replay for _, idempotent_replay, _ in results]
    statuses = [status for _, _, status in results]
    assert len(set(proof_ids)) == 1
    assert statuses == ["issued"] * THREAD_COUNT
    assert replay_flags.count(False) == 1
    assert replay_flags.count(True) == THREAD_COUNT - 1

    with client.app.state.container.database.session() as session:
        proofs = list(
            session.scalars(
                select(IssuedProof).where(
                    IssuedProof.action_intent_record_id
                    == intake["action_intent_record_id"],
                    IssuedProof.status == ProofIssuanceStatus.issued,
                )
            )
        )
        signing_operations = list(
            session.scalars(
                select(SigningOperationRecord).where(
                    SigningOperationRecord.issued_proof_id == proof_ids[0]
                )
            )
        )
    assert len(proofs) == 1
    assert len(signing_operations) == 1


def test_concurrent_escrow_consumes_allow_one_winner(client: TestClient) -> None:
    _, proof = create_issued_proof(client)
    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {
                "principal_type": "user",
                "principal_id": "release-manager-atomicity",
            },
        },
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()
    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {
                "principal_type": "user",
                "principal_id": "release-manager-atomicity",
            }
        },
    )
    assert release_response.status_code == 200
    token = release_response.json()["capability_token"]
    barrier = threading.Barrier(THREAD_COUNT)

    def worker(index: int) -> tuple[str, str]:
        with client.app.state.container.database.session() as session:
            service = _escrow_service(client, session)
            barrier.wait(timeout=10)
            try:
                record = service.consume_capability(
                    hold["escrow_record_id"],
                    capability_token=token,
                    consumed_by=EscrowActor(
                        principal_type="service_principal",
                        principal_id=f"payments-adapter-{index:03d}",
                    ),
                    provider_execution_ref=f"provider-exec-{index:03d}",
                    provider_status="accepted",
                    transition_metadata={"worker_index": index},
                )
            except EscrowStateError as exc:
                return ("already_consumed", str(exc))
            return ("consumed", record.provider_execution_ref or "")

    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        results = list(executor.map(worker, range(THREAD_COUNT)))

    outcomes = [outcome for outcome, _ in results]
    assert outcomes.count("consumed") == 1
    assert outcomes.count("already_consumed") == THREAD_COUNT - 1
    with client.app.state.container.database.session() as session:
        record = session.get(EscrowRecord, hold["escrow_record_id"])
        assert record is not None
        transitions = list(
            session.scalars(
                select(EscrowTransitionRecord).where(
                    EscrowTransitionRecord.escrow_record_id == hold["escrow_record_id"],
                    EscrowTransitionRecord.transition_type == EscrowTransitionType.consumed,
                )
            )
        )
    assert record.status == EscrowStatus.consumed
    assert len(transitions) == 1


def test_consumed_cloud_escrow_cannot_be_reused_after_new_session(
    client: TestClient,
) -> None:
    _, proof = create_issued_proof(client)
    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {
                "principal_type": "user",
                "principal_id": "release-manager-persistence",
            },
        },
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()
    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {
                "principal_type": "user",
                "principal_id": "release-manager-persistence",
            }
        },
    )
    assert release_response.status_code == 200
    token = release_response.json()["capability_token"]

    with client.app.state.container.database.session() as session:
        service = _escrow_service(client, session)
        consumed = service.consume_capability(
            hold["escrow_record_id"],
            capability_token=token,
            consumed_by=EscrowActor(
                principal_type="service_principal",
                principal_id="payments-adapter-persistence",
            ),
            provider_execution_ref="provider-exec-persistence",
            provider_status="accepted",
            transition_metadata={},
        )
    assert consumed.status == EscrowStatus.consumed

    with client.app.state.container.database.session() as session:
        service = _escrow_service(client, session)
        with pytest.raises(EscrowStateError):
            service.consume_capability(
                hold["escrow_record_id"],
                capability_token=token,
                consumed_by=EscrowActor(
                    principal_type="service_principal",
                    principal_id="payments-adapter-persistence-replay",
                ),
                provider_execution_ref="provider-exec-persistence-replay",
                provider_status="accepted",
                transition_metadata={},
            )
