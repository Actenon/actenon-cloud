from __future__ import annotations

import hashlib
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.metrics import get_metrics_registry
from app.models import (
    ActionIntentRecord,
    ApprovalState,
    ContractValidationStatus,
    DecisionState,
    EvidenceState,
    IssuedProof,
    ProofIssuanceStatus,
    ProofKind,
    SigningKeyPurpose,
    TrustTier,
)
from app.services.approvals import ApprovalService
from app.services.evidence import EvidenceService
from app.services.signing import (
    SigningKeyNotFoundError,
    SigningKeyStateError,
    SigningOutcome,
    SigningService,
    canonical_json,
)

workflow_logger = logging.getLogger("action_control_plane.workflow")


class ProofIssuanceError(RuntimeError):
    pass


class IssuedProofNotFoundError(LookupError):
    pass


@dataclass(slots=True)
class IssuerActor:
    principal_type: str
    principal_id: str


@dataclass(slots=True)
class IssuanceEligibility:
    eligible: bool
    reason: str | None
    trace: list[dict[str, Any]]


@dataclass(slots=True)
class IssuanceResult:
    proof: IssuedProof
    idempotent_replay: bool


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class IssuanceService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings,
        approval_service: ApprovalService,
        evidence_service: EvidenceService,
        signing_service: SigningService,
    ) -> None:
        self.session = session
        self.settings = settings
        self.approval_service = approval_service
        self.evidence_service = evidence_service
        self.signing_service = signing_service

    def issue_proof(
        self,
        *,
        action_intent_record_id: str,
        proof_kind: ProofKind,
        audience: str,
        scope: list[str],
        expires_in_seconds: int | None,
        requested_by: IssuerActor,
        signing_key_reference_id: str | None,
    ) -> IssuanceResult:
        started = perf_counter()
        issuance_counter = get_metrics_registry().counter(
            "action_control_plane_proof_issuance_total",
            "Proof issuance attempts by resulting proof status, proof kind, and replay status.",
            label_names=("proof_status", "proof_kind", "idempotent_replay"),
        )

        try:
            action_intent = self._get_action_intent(action_intent_record_id)
            self.approval_service.synchronize_action_intent_state(action_intent)
            self.evidence_service.synchronize_action_intent_state(action_intent)

            normalized_scope = sorted(set(scope))
            if not normalized_scope:
                raise ProofIssuanceError("proof scope must contain at least one scope value")

            scope_hash = self._scope_hash(normalized_scope)
            existing_proof = self._find_existing_proof(
                tenant_id=action_intent.tenant_id,
                action_intent_record_id=action_intent.action_intent_record_id,
                proof_kind=proof_kind,
                audience=audience,
                scope_hash=scope_hash,
                action_intent_digest=action_intent.action_intent_digest,
            )
            if existing_proof is not None:
                return self._idempotent_replay_result(
                    proof=existing_proof,
                    proof_kind=proof_kind,
                    requested_by=requested_by,
                    started=started,
                    issuance_counter=issuance_counter,
                )

            eligibility = self._evaluate_eligibility(action_intent)
            issued_now = utc_now()
            requested_ttl = expires_in_seconds or self.settings.proof_default_ttl_seconds
            expires_at = issued_now + timedelta(seconds=requested_ttl)
            if requested_ttl > self.settings.proof_max_ttl_seconds:
                raise ProofIssuanceError(
                    "requested proof expiry exceeds the configured maximum TTL"
                )

            issuer_name = self.settings.proof_issuer_name
            issuer_uri = self.settings.proof_issuer_uri
            trust_tier = TrustTier(self.settings.proof_issuer_trust_tier)
            signing_key = None
            algorithm = None

            proof = IssuedProof(
                issued_proof_id=uuid4().hex,
                tenant_id=action_intent.tenant_id,
                action_intent_record_id=action_intent.action_intent_record_id,
                signing_key_reference_id=(
                    signing_key.signing_key_reference_id if signing_key is not None else None
                ),
                proof_kind=proof_kind,
                status=(
                    ProofIssuanceStatus.requested
                    if eligibility.eligible
                    else ProofIssuanceStatus.rejected
                ),
                issuer_name=issuer_name,
                issuer_uri=issuer_uri,
                trust_tier=trust_tier,
                audience=audience,
                scope=normalized_scope,
                scope_hash=scope_hash,
                nonce=self._nonce(),
                action_intent_digest=action_intent.action_intent_digest,
                proof_payload={},
                proof_payload_digest="",
                signature=None,
                algorithm=algorithm,
                issued_by_principal_type=requested_by.principal_type,
                issued_by_principal_id=requested_by.principal_id,
                issuance_trace=eligibility.trace,
                failure_reason=eligibility.reason,
                expires_at=expires_at,
            )
            self.session.add(proof)
            try:
                self.session.flush()
            except IntegrityError as exc:
                self.session.rollback()
                existing_proof = self._find_existing_proof(
                    tenant_id=action_intent.tenant_id,
                    action_intent_record_id=action_intent.action_intent_record_id,
                    proof_kind=proof_kind,
                    audience=audience,
                    scope_hash=scope_hash,
                    action_intent_digest=action_intent.action_intent_digest,
                )
                if existing_proof is not None:
                    return self._idempotent_replay_result(
                        proof=existing_proof,
                        proof_kind=proof_kind,
                        requested_by=requested_by,
                        started=started,
                        issuance_counter=issuance_counter,
                    )
                raise ProofIssuanceError(
                    "active proof issuance already exists but could not be replayed"
                ) from exc

            if not eligibility.eligible:
                self.session.commit()
                self.session.refresh(proof)
                duration_ms = int((perf_counter() - started) * 1000)
                issuance_counter.inc(
                    proof_status=proof.status.value,
                    proof_kind=proof.proof_kind.value,
                    idempotent_replay="false",
                )
                workflow_logger.info(
                    "proof.issuance.rejected",
                    extra={
                        "event": "proof.issuance.rejected",
                        "tenant_id": proof.tenant_id,
                        "principal_type": requested_by.principal_type,
                        "principal_id": requested_by.principal_id,
                        "action_intent_record_id": proof.action_intent_record_id,
                        "issued_proof_id": proof.issued_proof_id,
                        "proof_kind": proof.proof_kind.value,
                        "proof_status": proof.status.value,
                        "approval_state": action_intent.approval_state.value,
                        "evidence_state": action_intent.evidence_state.value,
                        "decision_state": action_intent.decision_state.value,
                        "outcome": proof.status.value,
                        "duration_ms": duration_ms,
                    },
                )
                return IssuanceResult(proof=proof, idempotent_replay=False)

            try:
                signing_key = self.signing_service.resolve_key(
                    tenant_id=action_intent.tenant_id,
                    key_purpose=SigningKeyPurpose.pccb_signing,
                    signing_key_reference_id=signing_key_reference_id,
                )
            except (SigningKeyNotFoundError, SigningKeyStateError) as exc:
                proof.status = ProofIssuanceStatus.rejected
                proof.failure_reason = str(exc)
                self.session.add(proof)
                self.session.commit()
                self.session.refresh(proof)
                duration_ms = int((perf_counter() - started) * 1000)
                issuance_counter.inc(
                    proof_status=proof.status.value,
                    proof_kind=proof.proof_kind.value,
                    idempotent_replay="false",
                )
                workflow_logger.warning(
                    "proof.issuance.rejected",
                    extra={
                        "event": "proof.issuance.rejected",
                        "tenant_id": proof.tenant_id,
                        "principal_type": requested_by.principal_type,
                        "principal_id": requested_by.principal_id,
                        "action_intent_record_id": proof.action_intent_record_id,
                        "issued_proof_id": proof.issued_proof_id,
                        "proof_kind": proof.proof_kind.value,
                        "proof_status": proof.status.value,
                        "outcome": proof.status.value,
                        "duration_ms": duration_ms,
                        "error_class": exc.__class__.__name__,
                        "error_message": str(exc),
                    },
                )
                return IssuanceResult(proof=proof, idempotent_replay=False)

            proof.signing_key_reference_id = signing_key.signing_key_reference_id
            proof.issuer_name = signing_key.issuer_name
            proof.issuer_uri = signing_key.issuer_uri
            proof.trust_tier = signing_key.trust_tier
            proof.algorithm = signing_key.algorithm
            self.session.add(proof)

            payload = self._build_proof_payload(
                proof=proof,
                action_intent=action_intent,
            )
            proof.proof_payload = payload

            try:
                signing_outcome = self.signing_service.sign_proof(
                    issued_proof=proof,
                    key_reference=signing_key,
                    payload=payload,
                )
            except (SigningKeyNotFoundError, SigningKeyStateError, ProofIssuanceError) as exc:
                proof.status = ProofIssuanceStatus.rejected
                proof.failure_reason = str(exc)
                proof.proof_payload_digest = self._digest_json(payload)
                self.session.add(proof)
                self.session.commit()
                self.session.refresh(proof)
                duration_ms = int((perf_counter() - started) * 1000)
                issuance_counter.inc(
                    proof_status=proof.status.value,
                    proof_kind=proof.proof_kind.value,
                    idempotent_replay="false",
                )
                workflow_logger.warning(
                    "proof.issuance.rejected",
                    extra={
                        "event": "proof.issuance.rejected",
                        "tenant_id": proof.tenant_id,
                        "principal_type": requested_by.principal_type,
                        "principal_id": requested_by.principal_id,
                        "action_intent_record_id": proof.action_intent_record_id,
                        "issued_proof_id": proof.issued_proof_id,
                        "proof_kind": proof.proof_kind.value,
                        "proof_status": proof.status.value,
                        "outcome": proof.status.value,
                        "duration_ms": duration_ms,
                        "error_class": exc.__class__.__name__,
                        "error_message": str(exc),
                    },
                )
                return IssuanceResult(proof=proof, idempotent_replay=False)
            except Exception as exc:
                proof.status = ProofIssuanceStatus.failed
                proof.failure_reason = str(exc)
                proof.proof_payload_digest = self._digest_json(payload)
                self.session.add(proof)
                self.session.commit()
                self.session.refresh(proof)
                duration_ms = int((perf_counter() - started) * 1000)
                issuance_counter.inc(
                    proof_status=proof.status.value,
                    proof_kind=proof.proof_kind.value,
                    idempotent_replay="false",
                )
                workflow_logger.exception(
                    "proof.issuance.failed",
                    extra={
                        "event": "proof.issuance.failed",
                        "tenant_id": proof.tenant_id,
                        "principal_type": requested_by.principal_type,
                        "principal_id": requested_by.principal_id,
                        "action_intent_record_id": proof.action_intent_record_id,
                        "issued_proof_id": proof.issued_proof_id,
                        "proof_kind": proof.proof_kind.value,
                        "proof_status": proof.status.value,
                        "outcome": proof.status.value,
                        "duration_ms": duration_ms,
                        "error_class": exc.__class__.__name__,
                        "error_message": str(exc),
                    },
                )
                return IssuanceResult(proof=proof, idempotent_replay=False)

            try:
                self._mark_proof_issued(proof=proof, signing_outcome=signing_outcome)
                self.session.commit()
                self.session.refresh(proof)
            except IntegrityError:
                self.session.rollback()
                existing_proof = self._find_existing_proof(
                    tenant_id=action_intent.tenant_id,
                    action_intent_record_id=action_intent.action_intent_record_id,
                    proof_kind=proof_kind,
                    audience=audience,
                    scope_hash=scope_hash,
                    action_intent_digest=action_intent.action_intent_digest,
                )
                if existing_proof is not None:
                    return self._idempotent_replay_result(
                        proof=existing_proof,
                        proof_kind=proof_kind,
                        requested_by=requested_by,
                        started=started,
                        issuance_counter=issuance_counter,
                    )
                raise
            duration_ms = int((perf_counter() - started) * 1000)
            issuance_counter.inc(
                proof_status=proof.status.value,
                proof_kind=proof.proof_kind.value,
                idempotent_replay="false",
            )
            workflow_logger.info(
                "proof.issuance.completed",
                extra={
                    "event": "proof.issuance.completed",
                    "tenant_id": proof.tenant_id,
                    "principal_type": requested_by.principal_type,
                    "principal_id": requested_by.principal_id,
                    "action_intent_record_id": proof.action_intent_record_id,
                    "issued_proof_id": proof.issued_proof_id,
                    "proof_kind": proof.proof_kind.value,
                    "proof_status": proof.status.value,
                    "outcome": proof.status.value,
                    "duration_ms": duration_ms,
                },
            )
            return IssuanceResult(proof=proof, idempotent_replay=False)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            issuance_counter.inc(
                proof_status="error",
                proof_kind=proof_kind.value,
                idempotent_replay="false",
            )
            log_method = (
                workflow_logger.warning
                if isinstance(exc, ProofIssuanceError)
                else workflow_logger.exception
            )
            log_method(
                "proof.issuance.failed",
                extra={
                    "event": "proof.issuance.failed",
                    "principal_type": requested_by.principal_type,
                    "principal_id": requested_by.principal_id,
                    "action_intent_record_id": action_intent_record_id,
                    "proof_kind": proof_kind.value,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            raise

    def list_proofs(
        self,
        *,
        tenant_id: str | None = None,
        action_intent_record_id: str | None = None,
        status: ProofIssuanceStatus | None = None,
    ) -> list[IssuedProof]:
        query = self._proof_query().order_by(IssuedProof.created_at.asc())
        if tenant_id is not None:
            query = query.where(IssuedProof.tenant_id == tenant_id)
        if action_intent_record_id is not None:
            query = query.where(IssuedProof.action_intent_record_id == action_intent_record_id)
        if status is not None:
            query = query.where(IssuedProof.status == status)

        proofs = list(self.session.scalars(query))
        changed = False
        for proof in proofs:
            if self._refresh_if_expired(proof):
                changed = True
        if changed:
            self.session.commit()
            proofs = list(self.session.scalars(query))
        return proofs

    def get_proof(self, issued_proof_id: str) -> IssuedProof:
        proof = self.session.scalar(
            self._proof_query().where(IssuedProof.issued_proof_id == issued_proof_id)
        )
        if proof is None:
            raise IssuedProofNotFoundError(f"issued proof '{issued_proof_id}' was not found")

        if self._refresh_if_expired(proof):
            self.session.commit()
            proof = self.session.scalar(
                self._proof_query().where(IssuedProof.issued_proof_id == issued_proof_id)
            )
            if proof is None:
                raise RuntimeError("issued proof disappeared during status refresh")
        return proof

    def _idempotent_replay_result(
        self,
        *,
        proof: IssuedProof,
        proof_kind: ProofKind,
        requested_by: IssuerActor,
        started: float,
        issuance_counter: Any,
    ) -> IssuanceResult:
        duration_ms = int((perf_counter() - started) * 1000)
        issuance_counter.inc(
            proof_status=proof.status.value,
            proof_kind=proof_kind.value,
            idempotent_replay="true",
        )
        workflow_logger.info(
            "proof.issuance.replayed",
            extra={
                "event": "proof.issuance.replayed",
                "tenant_id": proof.tenant_id,
                "principal_type": requested_by.principal_type,
                "principal_id": requested_by.principal_id,
                "action_intent_record_id": proof.action_intent_record_id,
                "issued_proof_id": proof.issued_proof_id,
                "proof_kind": proof.proof_kind.value,
                "proof_status": proof.status.value,
                "outcome": proof.status.value,
                "idempotent_replay": True,
                "duration_ms": duration_ms,
            },
        )
        return IssuanceResult(proof=proof, idempotent_replay=True)

    def _proof_query(self):
        return select(IssuedProof).options(
            selectinload(IssuedProof.signing_key),
            selectinload(IssuedProof.signing_operations),
        )

    def _get_action_intent(self, action_intent_record_id: str) -> ActionIntentRecord:
        action_intent = self.session.get(ActionIntentRecord, action_intent_record_id)
        if action_intent is None:
            raise ProofIssuanceError(
                f"action intent record '{action_intent_record_id}' was not found"
            )
        return action_intent

    def _find_existing_proof(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        proof_kind: ProofKind,
        audience: str,
        scope_hash: str,
        action_intent_digest: str,
    ) -> IssuedProof | None:
        proof = self.session.scalar(
            self._proof_query().where(
                IssuedProof.tenant_id == tenant_id,
                IssuedProof.action_intent_record_id == action_intent_record_id,
                IssuedProof.proof_kind == proof_kind,
                IssuedProof.audience == audience,
                IssuedProof.scope_hash == scope_hash,
                IssuedProof.action_intent_digest == action_intent_digest,
                IssuedProof.status == ProofIssuanceStatus.issued,
            )
        )
        if proof is None:
            return None
        if self._refresh_if_expired(proof):
            return None
        return proof

    def _evaluate_eligibility(self, action_intent: ActionIntentRecord) -> IssuanceEligibility:
        trace: list[dict[str, Any]] = []
        failures: list[str] = []

        contract_valid = action_intent.contract_validation_status == ContractValidationStatus.valid
        trace.append(
            {
                "check": "contract_validation",
                "passed": contract_valid,
                "actual": action_intent.contract_validation_status.value,
            }
        )
        if not contract_valid:
            failures.append("Action Intent contract validation is not valid")

        decision_permitted = action_intent.decision_state not in {
            DecisionState.deny,
            DecisionState.structurally_non_executable,
        }
        trace.append(
            {
                "check": "policy_decision",
                "passed": decision_permitted,
                "actual": action_intent.decision_state.value,
            }
        )
        if not decision_permitted:
            failures.append("policy result does not permit proof issuance")

        approval_satisfied = (
            not action_intent.approval_requirement
            or action_intent.approval_state == ApprovalState.satisfied
        )
        trace.append(
            {
                "check": "approval_state",
                "passed": approval_satisfied,
                "actual": action_intent.approval_state.value,
            }
        )
        if not approval_satisfied:
            failures.append("required approvals are not satisfied")

        evidence_satisfied = (
            not action_intent.evidence_requirement
            or action_intent.evidence_state == EvidenceState.satisfied
        )
        trace.append(
            {
                "check": "evidence_state",
                "passed": evidence_satisfied,
                "actual": action_intent.evidence_state.value,
            }
        )
        if not evidence_satisfied:
            failures.append("required evidence is not satisfied")

        return IssuanceEligibility(
            eligible=not failures,
            reason="; ".join(failures) if failures else None,
            trace=trace,
        )

    def _build_proof_payload(
        self,
        *,
        proof: IssuedProof,
        action_intent: ActionIntentRecord,
    ) -> dict[str, Any]:
        issued_at = utc_now()
        return {
            "proof_kind": proof.proof_kind.value,
            "issuer": {
                "name": proof.issuer_name,
                "uri": proof.issuer_uri,
                "trust_tier": proof.trust_tier.value,
            },
            "subject": {
                "tenant_id": action_intent.tenant_id,
                "action_intent_record_id": action_intent.action_intent_record_id,
                "external_action_intent_id": action_intent.external_action_intent_id,
            },
            "binding": {
                "contract_version_ref": action_intent.contract_version_ref,
                "action_intent_digest": action_intent.action_intent_digest,
                "audience": proof.audience,
                "scope": proof.scope,
                "scope_hash": proof.scope_hash,
                "nonce": proof.nonce,
                "issued_at": issued_at.isoformat(),
                "expires_at": normalize_utc(proof.expires_at).isoformat(),
            },
            "governance": {
                "policy_id": action_intent.policy_id,
                "policy_version": action_intent.policy_version,
                "decision_state": action_intent.decision_state.value,
                "approval_state": action_intent.approval_state.value,
                "evidence_state": action_intent.evidence_state.value,
                "matched_rule_id": action_intent.matched_rule_id,
            },
            "finance": {
                "workflow_key": action_intent.workflow_key,
                "action_type": action_intent.finance_index.get("action_type"),
                "amount_minor": action_intent.finance_index.get("amount_minor"),
                "currency": action_intent.finance_index.get("currency"),
                "source_account_ref": action_intent.finance_index.get("source_account_ref"),
                "destination_account_ref": action_intent.finance_index.get(
                    "destination_account_ref"
                ),
            },
        }

    def _mark_proof_issued(
        self,
        *,
        proof: IssuedProof,
        signing_outcome: SigningOutcome,
    ) -> None:
        proof.status = ProofIssuanceStatus.issued
        proof.signature = signing_outcome.signature
        proof.proof_payload_digest = signing_outcome.payload_digest
        proof.issued_at = utc_now()
        self.session.add(proof)

    def _refresh_if_expired(self, proof: IssuedProof) -> bool:
        if proof.status != ProofIssuanceStatus.issued:
            return False
        if normalize_utc(proof.expires_at) > utc_now():
            return False
        proof.status = ProofIssuanceStatus.expired
        self.session.add(proof)
        return True

    def _scope_hash(self, scope: list[str]) -> str:
        return hashlib.sha256(json.dumps(scope, separators=(",", ":")).encode("utf-8")).hexdigest()

    def _nonce(self) -> str:
        return secrets.token_urlsafe(24)

    def _digest_json(self, payload: dict[str, Any]) -> str:
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
