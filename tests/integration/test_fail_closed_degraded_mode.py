from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActionIntentRecord, IssuedProof, ProofKind
from app.services.action_intents import ActionIntentService, KernelContractRegistry
from app.services.approvals import ApprovalService
from app.services.evidence import EvidenceService
from app.services.issuance import IssuanceService, IssuerActor
from app.services.policy_engine import PolicyEngine, PolicyManagementService
from app.services.signing import SigningService
from tests.integration.test_issuance import (
    build_intake_payload,
    create_policy_with_controls,
    create_signing_key,
    create_tenant,
)


class _PolicyServiceUnavailable(PolicyManagementService):
    def get_active_policy(self, tenant_id: str, workflow_key: str):  # type: ignore[no-untyped-def]
        raise RuntimeError("policy service unavailable")


class _EvidenceServiceUnavailable:
    def synchronize_action_intent_state(self, action_intent: ActionIntentRecord) -> None:
        raise RuntimeError("evidence store unavailable")


def _evidence_service(client: TestClient, session: Session) -> EvidenceService:
    return EvidenceService.from_settings(session, settings=client.app.state.container.settings)


def test_policy_service_unavailable_fails_closed_before_action_intent_is_recorded(
    client: TestClient,
) -> None:
    tenant = create_tenant(client)
    submission_id = "fail-closed-policy-submission"
    idempotency_key = "fail-closed-policy-idempotency"
    payload = build_intake_payload(
        tenant["tenant_id"],
        submission_id=submission_id,
        idempotency_key=idempotency_key,
        evaluation_context={"risk_tier": "low", "evidence_present": True},
    )

    with client.app.state.container.database.session() as session:
        service = ActionIntentService(
            session,
            contract_registry=KernelContractRegistry(),
            policy_service=_PolicyServiceUnavailable(session),
            policy_engine=PolicyEngine(),
            approval_service=ApprovalService(session),
            evidence_service=_evidence_service(client, session),
        )

        with pytest.raises(RuntimeError, match="policy service unavailable"):
            service.intake(payload)

        records = list(
            session.scalars(
                select(ActionIntentRecord).where(
                    ActionIntentRecord.tenant_id == tenant["tenant_id"],
                    ActionIntentRecord.submission_id == submission_id,
                    ActionIntentRecord.idempotency_key == idempotency_key,
                )
            )
        )
        proofs = list(session.scalars(select(IssuedProof)))

    assert records == []
    assert proofs == []


def test_evidence_store_unavailable_fails_closed_before_proof_is_issued(
    client: TestClient,
) -> None:
    tenant = create_tenant(client)
    create_policy_with_controls(client, tenant["tenant_id"])
    key = create_signing_key(client, tenant["tenant_id"])
    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="fail-closed-evidence-submission",
            idempotency_key="fail-closed-evidence-idempotency",
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()
    assert intake["evidence_requirement"] is not None

    with client.app.state.container.database.session() as session:
        service = IssuanceService(
            session,
            settings=client.app.state.container.settings,
            approval_service=ApprovalService(session),
            evidence_service=_EvidenceServiceUnavailable(),  # type: ignore[arg-type]
            signing_service=SigningService(
                session,
                settings=client.app.state.container.settings,
            ),
        )

        with pytest.raises(RuntimeError, match="evidence store unavailable"):
            service.issue_proof(
                action_intent_record_id=intake["action_intent_record_id"],
                proof_kind=ProofKind.pccb,
                audience="finance-ops.internal",
                scope=["finance.transfer.release"],
                expires_in_seconds=None,
                requested_by=IssuerActor(
                    principal_type="user",
                    principal_id="issuer-fail-closed-001",
                ),
                signing_key_reference_id=key["signing_key_reference_id"],
            )

        proofs = list(
            session.scalars(
                select(IssuedProof).where(
                    IssuedProof.action_intent_record_id == intake["action_intent_record_id"]
                )
            )
        )

    assert proofs == []


def test_missing_policy_defaults_to_non_executable_proof_status(client: TestClient) -> None:
    tenant = create_tenant(client)
    key = create_signing_key(client, tenant["tenant_id"])
    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id="fail-closed-no-policy-submission",
            idempotency_key="fail-closed-no-policy-idempotency",
            evaluation_context={"risk_tier": "low", "evidence_present": True},
        ),
    )
    assert intake_response.status_code == 201
    intake = intake_response.json()
    assert intake["decision_state"] == "deny"

    proof_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-ops.internal",
            "scope": ["finance.transfer.release"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "issuer-fail-closed-002",
            },
            "signing_key_reference_id": key["signing_key_reference_id"],
        },
    )
    assert proof_response.status_code == 201
    proof = proof_response.json()
    assert proof["status"] == "rejected"
    assert proof["signature"] is None
    assert "policy result does not permit proof issuance" in proof["failure_reason"]
