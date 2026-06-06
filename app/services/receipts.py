from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from jsonschema import Draft202012Validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.metrics import get_metrics_registry
from app.models import (
    ActionIntentRecord,
    ApprovalDecision,
    ApprovalRequest,
    EscrowRecord,
    EvidenceObject,
    ExecutionState,
    IssuedProof,
    ReceiptRecord,
    ReceiptState,
    ReconciliationRecord,
    ReconciliationStatus,
    ReconciliationType,
)
from app.services.audit import AuditActor, AuditService

workflow_logger = logging.getLogger("action_control_plane.workflow")

SUPPORTED_RECEIPT_CONTRACTS = {
    "open_execution_kernel.receipt.finance.v1alpha1": (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "kernel"
        / "receipt.finance.v1alpha1.schema.json"
    )
}


class ReceiptNotFoundError(LookupError):
    pass


class ReceiptIngestionError(ValueError):
    pass


@dataclass(slots=True)
class ContractValidationResult:
    supported: bool
    valid: bool
    errors: list[str]


@dataclass(slots=True)
class ReceiptActor:
    principal_type: str
    principal_id: str


@dataclass(slots=True)
class ReceiptIngestionResult:
    receipt: ReceiptRecord
    idempotent_replay: bool


@lru_cache
def _validator_for_version(version_ref: str) -> Draft202012Validator | None:
    schema_path = SUPPORTED_RECEIPT_CONTRACTS.get(version_ref)
    if schema_path is None:
        return None
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ReceiptContractRegistry:
    def validate_receipt(
        self,
        *,
        contract_family: str,
        version_ref: str,
        payload: dict[str, Any],
    ) -> ContractValidationResult:
        if contract_family != "receipt":
            return ContractValidationResult(
                supported=False,
                valid=False,
                errors=[f"unsupported contract family '{contract_family}'"],
            )

        validator = _validator_for_version(version_ref)
        if validator is None:
            return ContractValidationResult(
                supported=False,
                valid=False,
                errors=[f"unsupported contract version '{version_ref}'"],
            )

        errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
        if not errors:
            return ContractValidationResult(supported=True, valid=True, errors=[])

        formatted_errors = []
        for error in errors:
            location = ".".join(str(segment) for segment in error.absolute_path)
            formatted_errors.append(
                f"{location}: {error.message}" if location else error.message
            )
        return ContractValidationResult(supported=True, valid=False, errors=formatted_errors)


class ReceiptService:
    def __init__(
        self,
        session: Session,
        *,
        audit_service: AuditService,
        contract_registry: ReceiptContractRegistry | None = None,
    ) -> None:
        self.session = session
        self.audit_service = audit_service
        self.contract_registry = contract_registry or ReceiptContractRegistry()

    def ingest_receipt(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        contract_family: str,
        contract_version_ref: str,
        kernel_receipt: dict[str, Any],
        received_by: ReceiptActor,
        issued_proof_id: str | None,
        escrow_record_id: str | None,
    ) -> ReceiptIngestionResult:
        started = perf_counter()
        receipt_counter = get_metrics_registry().counter(
            "action_control_plane_receipt_ingestions_total",
            "Receipt ingestions by receipt state, contract validation status, outcome, and replay.",
            label_names=(
                "receipt_state",
                "contract_validation_status",
                "outcome",
                "idempotent_replay",
            ),
        )

        try:
            action_intent = self._get_action_intent(tenant_id, action_intent_record_id)
            validation = self.contract_registry.validate_receipt(
                contract_family=contract_family,
                version_ref=contract_version_ref,
                payload=kernel_receipt,
            )
            digest = self._digest(kernel_receipt)
            existing = self.session.scalar(
                select(ReceiptRecord).where(
                    ReceiptRecord.tenant_id == tenant_id,
                    ReceiptRecord.kernel_receipt_digest == digest,
                )
            )
            if existing is not None:
                duration_ms = int((perf_counter() - started) * 1000)
                receipt_counter.inc(
                    receipt_state=existing.receipt_state.value,
                    contract_validation_status=str(existing.contract_validation_status),
                    outcome=existing.outcome,
                    idempotent_replay="true",
                )
                workflow_logger.info(
                    "receipt.ingestion.replayed",
                    extra={
                        "event": "receipt.ingestion.replayed",
                        "tenant_id": existing.tenant_id,
                        "principal_type": received_by.principal_type,
                        "principal_id": received_by.principal_id,
                        "action_intent_record_id": existing.action_intent_record_id,
                        "receipt_id": existing.receipt_id,
                        "receipt_state": existing.receipt_state.value,
                        "contract_validation_status": str(existing.contract_validation_status),
                        "outcome": existing.outcome,
                        "idempotent_replay": True,
                        "duration_ms": duration_ms,
                    },
                )
                return ReceiptIngestionResult(receipt=existing, idempotent_replay=True)

            proof = self._get_issued_proof(tenant_id, action_intent_record_id, issued_proof_id)
            escrow = self._get_escrow_record(tenant_id, action_intent_record_id, escrow_record_id)
            receipt_timestamp = self._parse_timestamp(kernel_receipt["occurred_at"])
            linked_ids = self._linked_workflow_ids(action_intent_record_id)
            receipt_index = self._build_receipt_index(action_intent, kernel_receipt)

            receipt = ReceiptRecord(
                receipt_id=uuid4().hex,
                tenant_id=tenant_id,
                action_intent_record_id=action_intent_record_id,
                issued_proof_id=proof.issued_proof_id if proof is not None else None,
                escrow_record_id=escrow.escrow_record_id if escrow is not None else None,
                contract_family=contract_family,
                contract_version_ref=contract_version_ref,
                contract_validation_status=self._validation_status(validation),
                contract_validation_errors=validation.errors,
                external_receipt_id=str(kernel_receipt["receipt_id"]),
                receipt_type=str(kernel_receipt["receipt_type"]),
                outcome=str(kernel_receipt["outcome"]),
                receipt_timestamp=receipt_timestamp,
                kernel_receipt_digest=digest,
                receipt_payload=kernel_receipt,
                receipt_index=receipt_index,
                linked_approval_request_ids=linked_ids["approval_request_ids"],
                linked_approval_decision_ids=linked_ids["approval_decision_ids"],
                linked_evidence_object_ids=linked_ids["evidence_object_ids"],
                provider_execution_ref=kernel_receipt.get("provider_execution_ref"),
                settlement_reference=kernel_receipt.get("settlement_reference"),
                received_by_principal_type=received_by.principal_type,
                received_by_principal_id=received_by.principal_id,
                receipt_state=ReceiptState.received,
                reconciliation_summary={},
            )
            self.session.add(receipt)
            self.session.flush()

            audit_actor = AuditActor(
                principal_type=received_by.principal_type,
                principal_id=received_by.principal_id,
            )
            self.audit_service.record_event(
                tenant_id=tenant_id,
                action_intent_record_id=action_intent_record_id,
                receipt_id=receipt.receipt_id,
                issued_proof_id=receipt.issued_proof_id,
                escrow_record_id=receipt.escrow_record_id,
                event_category="receipt",
                event_type="receipt.ingested",
                subject_type="receipt_record",
                subject_id=receipt.receipt_id,
                actor=audit_actor,
                event_payload={
                    "contract_family": contract_family,
                    "contract_version_ref": contract_version_ref,
                    "contract_validation_status": receipt.contract_validation_status,
                    "external_receipt_id": receipt.external_receipt_id,
                    "receipt_type": receipt.receipt_type,
                    "outcome": receipt.outcome,
                },
            )

            reconciliation_records = self._run_reconciliation_hooks(
                action_intent=action_intent,
                receipt=receipt,
                proof=proof,
                escrow=escrow,
                actor=audit_actor,
            )

            receipt.receipt_state = ReceiptState.indexed
            receipt.reconciliation_summary = self._reconciliation_summary(reconciliation_records)
            if reconciliation_records and all(
                record.status == ReconciliationStatus.matched for record in reconciliation_records
            ):
                receipt.receipt_state = ReceiptState.reconciled

            self._apply_lifecycle_effects(action_intent, receipt)
            self.session.add(receipt)
            self.session.add(action_intent)
            self.session.commit()
            self.session.refresh(receipt)

            duration_ms = int((perf_counter() - started) * 1000)
            receipt_counter.inc(
                receipt_state=receipt.receipt_state.value,
                contract_validation_status=str(receipt.contract_validation_status),
                outcome=receipt.outcome,
                idempotent_replay="false",
            )
            workflow_logger.info(
                "receipt.ingested",
                extra={
                    "event": "receipt.ingested",
                    "tenant_id": receipt.tenant_id,
                    "principal_type": received_by.principal_type,
                    "principal_id": received_by.principal_id,
                    "action_intent_record_id": receipt.action_intent_record_id,
                    "receipt_id": receipt.receipt_id,
                    "receipt_state": receipt.receipt_state.value,
                    "execution_state": action_intent.execution_state.value,
                    "contract_validation_status": str(receipt.contract_validation_status),
                    "outcome": receipt.outcome,
                    "duration_ms": duration_ms,
                },
            )
            return ReceiptIngestionResult(receipt=receipt, idempotent_replay=False)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            receipt_counter.inc(
                receipt_state="error",
                contract_validation_status="unknown",
                outcome="error",
                idempotent_replay="false",
            )
            log_method = (
                workflow_logger.warning
                if isinstance(exc, ReceiptIngestionError)
                else workflow_logger.exception
            )
            log_method(
                "receipt.ingestion.failed",
                extra={
                    "event": "receipt.ingestion.failed",
                    "tenant_id": tenant_id,
                    "principal_type": received_by.principal_type,
                    "principal_id": received_by.principal_id,
                    "action_intent_record_id": action_intent_record_id,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            raise

    def list_receipts(
        self,
        *,
        tenant_id: str | None = None,
        action_intent_record_id: str | None = None,
        issued_proof_id: str | None = None,
        escrow_record_id: str | None = None,
        receipt_type: str | None = None,
        outcome: str | None = None,
        currency: str | None = None,
        provider_execution_ref: str | None = None,
    ) -> list[ReceiptRecord]:
        query = select(ReceiptRecord).order_by(ReceiptRecord.receipt_timestamp.asc())
        if tenant_id is not None:
            query = query.where(ReceiptRecord.tenant_id == tenant_id)
        if action_intent_record_id is not None:
            query = query.where(ReceiptRecord.action_intent_record_id == action_intent_record_id)
        if issued_proof_id is not None:
            query = query.where(ReceiptRecord.issued_proof_id == issued_proof_id)
        if escrow_record_id is not None:
            query = query.where(ReceiptRecord.escrow_record_id == escrow_record_id)
        if receipt_type is not None:
            query = query.where(ReceiptRecord.receipt_type == receipt_type)
        if outcome is not None:
            query = query.where(ReceiptRecord.outcome == outcome)
        if currency is not None:
            query = query.where(ReceiptRecord.receipt_index["currency"].as_string() == currency)
        if provider_execution_ref is not None:
            query = query.where(ReceiptRecord.provider_execution_ref == provider_execution_ref)
        return list(self.session.scalars(query))

    def get_receipt(self, receipt_id: str) -> ReceiptRecord:
        receipt = self.session.get(ReceiptRecord, receipt_id)
        if receipt is None:
            raise ReceiptNotFoundError(f"receipt '{receipt_id}' was not found")
        return receipt

    def _get_action_intent(
        self,
        tenant_id: str,
        action_intent_record_id: str,
    ) -> ActionIntentRecord:
        action_intent = self.session.get(ActionIntentRecord, action_intent_record_id)
        if action_intent is None or action_intent.tenant_id != tenant_id:
            raise ReceiptIngestionError(
                f"action intent record '{action_intent_record_id}' was not found for tenant"
            )
        return action_intent

    def _get_issued_proof(
        self,
        tenant_id: str,
        action_intent_record_id: str,
        issued_proof_id: str | None,
    ) -> IssuedProof | None:
        if issued_proof_id is None:
            return None
        proof = self.session.get(IssuedProof, issued_proof_id)
        if proof is None:
            raise ReceiptIngestionError(f"issued proof '{issued_proof_id}' was not found")
        if proof.tenant_id != tenant_id or proof.action_intent_record_id != action_intent_record_id:
            raise ReceiptIngestionError(
                "issued proof does not belong to the provided tenant and Action Intent"
            )
        return proof

    def _get_escrow_record(
        self,
        tenant_id: str,
        action_intent_record_id: str,
        escrow_record_id: str | None,
    ) -> EscrowRecord | None:
        if escrow_record_id is None:
            return None
        escrow = self.session.get(EscrowRecord, escrow_record_id)
        if escrow is None:
            raise ReceiptIngestionError(f"escrow record '{escrow_record_id}' was not found")
        if (
            escrow.tenant_id != tenant_id
            or escrow.action_intent_record_id != action_intent_record_id
        ):
            raise ReceiptIngestionError(
                "escrow record does not belong to the provided tenant and Action Intent"
            )
        return escrow

    def _linked_workflow_ids(self, action_intent_record_id: str) -> dict[str, list[str]]:
        approval_requests = list(
            self.session.scalars(
                select(ApprovalRequest.approval_request_id).where(
                    ApprovalRequest.action_intent_record_id == action_intent_record_id
                )
            )
        )
        approval_decisions = list(
            self.session.scalars(
                select(ApprovalDecision.approval_decision_id)
                .join(
                    ApprovalRequest,
                    ApprovalDecision.approval_request_id == ApprovalRequest.approval_request_id,
                )
                .where(ApprovalRequest.action_intent_record_id == action_intent_record_id)
            )
        )
        evidence_object_ids = list(
            self.session.scalars(
                select(EvidenceObject.evidence_object_id).where(
                    EvidenceObject.action_intent_record_id == action_intent_record_id
                )
            )
        )
        return {
            "approval_request_ids": approval_requests,
            "approval_decision_ids": approval_decisions,
            "evidence_object_ids": evidence_object_ids,
        }

    def _run_reconciliation_hooks(
        self,
        *,
        action_intent: ActionIntentRecord,
        receipt: ReceiptRecord,
        proof: IssuedProof | None,
        escrow: EscrowRecord | None,
        actor: AuditActor,
    ) -> list[ReconciliationRecord]:
        records = [
            self._create_reconciliation_record(
                action_intent=action_intent,
                receipt=receipt,
                proof=proof,
                escrow=escrow,
                reconciliation_type=ReconciliationType.intent_to_receipt,
                actor=actor,
            )
        ]
        if proof is not None:
            records.append(
                self._create_reconciliation_record(
                    action_intent=action_intent,
                    receipt=receipt,
                    proof=proof,
                    escrow=escrow,
                    reconciliation_type=ReconciliationType.proof_to_receipt,
                    actor=actor,
                )
            )
        if escrow is not None:
            records.append(
                self._create_reconciliation_record(
                    action_intent=action_intent,
                    receipt=receipt,
                    proof=proof,
                    escrow=escrow,
                    reconciliation_type=ReconciliationType.escrow_to_receipt,
                    actor=actor,
                )
            )
        return records

    def _create_reconciliation_record(
        self,
        *,
        action_intent: ActionIntentRecord,
        receipt: ReceiptRecord,
        proof: IssuedProof | None,
        escrow: EscrowRecord | None,
        reconciliation_type: ReconciliationType,
        actor: AuditActor,
    ) -> ReconciliationRecord:
        checks: list[dict[str, Any]]
        if reconciliation_type == ReconciliationType.intent_to_receipt:
            checks = [
                self._check(
                    "intent_id",
                    expected=action_intent.external_action_intent_id,
                    actual=receipt.receipt_payload.get("intent_id"),
                ),
                self._check(
                    "action_intent_digest",
                    expected=action_intent.action_intent_digest,
                    actual=receipt.receipt_payload.get("action_intent_digest"),
                ),
                self._check(
                    "action_type",
                    expected=action_intent.finance_index.get("action_type"),
                    actual=receipt.receipt_payload.get("action_type"),
                ),
                self._check(
                    "amount_minor",
                    expected=action_intent.finance_index.get("amount_minor"),
                    actual=receipt.receipt_payload.get("amount_minor"),
                ),
                self._check(
                    "currency",
                    expected=action_intent.finance_index.get("currency"),
                    actual=receipt.receipt_payload.get("currency"),
                ),
            ]
        elif reconciliation_type == ReconciliationType.proof_to_receipt:
            if proof is None:
                raise ReceiptIngestionError("proof reconciliation requires an issued proof")
            checks = [
                self._check(
                    "proof_nonce",
                    expected=proof.nonce,
                    actual=receipt.receipt_payload.get("proof_nonce"),
                    required=False,
                ),
                self._check(
                    "audience",
                    expected=proof.audience,
                    actual=receipt.receipt_payload.get("audience"),
                    required=False,
                ),
                self._check(
                    "scope",
                    expected=list(proof.scope),
                    actual=receipt.receipt_payload.get("scope"),
                    required=False,
                ),
                self._check(
                    "action_intent_digest",
                    expected=proof.action_intent_digest,
                    actual=receipt.receipt_payload.get("action_intent_digest"),
                ),
            ]
        else:
            if escrow is None:
                raise ReceiptIngestionError("escrow reconciliation requires an escrow record")
            checks = [
                self._check(
                    "provider_execution_ref",
                    expected=escrow.provider_execution_ref,
                    actual=receipt.provider_execution_ref,
                    required=False,
                ),
                self._check(
                    "action_intent_digest",
                    expected=escrow.action_intent_digest,
                    actual=receipt.receipt_payload.get("action_intent_digest"),
                ),
                self._check(
                    "scope",
                    expected=list(escrow.scope),
                    actual=receipt.receipt_payload.get("scope"),
                    required=False,
                ),
            ]

        status = self._reconciliation_status(checks)
        summary = self._reconciliation_summary_text(reconciliation_type, status, checks)
        record = ReconciliationRecord(
            reconciliation_record_id=uuid4().hex,
            tenant_id=action_intent.tenant_id,
            action_intent_record_id=action_intent.action_intent_record_id,
            receipt_id=receipt.receipt_id,
            issued_proof_id=proof.issued_proof_id if proof is not None else None,
            escrow_record_id=escrow.escrow_record_id if escrow is not None else None,
            reconciliation_type=reconciliation_type,
            status=status,
            hook_name="receipt_ingestion",
            summary=summary,
            checks=checks,
        )
        self.session.add(record)
        self.session.flush()

        self.audit_service.record_event(
            tenant_id=action_intent.tenant_id,
            action_intent_record_id=action_intent.action_intent_record_id,
            receipt_id=receipt.receipt_id,
            issued_proof_id=record.issued_proof_id,
            escrow_record_id=record.escrow_record_id,
            event_category="reconciliation",
            event_type=f"reconciliation.{reconciliation_type.value}.{status.value}",
            subject_type="reconciliation_record",
            subject_id=record.reconciliation_record_id,
            actor=actor,
            event_payload={
                "hook_name": record.hook_name,
                "summary": summary,
                "checks": checks,
            },
        )
        return record

    def _apply_lifecycle_effects(
        self,
        action_intent: ActionIntentRecord,
        receipt: ReceiptRecord,
    ) -> None:
        action_intent.latest_receipt_id = receipt.receipt_id
        action_intent.receipt_state = receipt.receipt_state
        if receipt.outcome == "succeeded":
            action_intent.execution_state = ExecutionState.result_observed
        elif receipt.outcome == "failed":
            action_intent.execution_state = ExecutionState.failure_observed
        else:
            action_intent.execution_state = ExecutionState.dispatch_confirmed

    def _reconciliation_summary(
        self,
        reconciliation_records: list[ReconciliationRecord],
    ) -> dict[str, Any]:
        return {
            "hook_name": "receipt_ingestion",
            "overall_status": (
                "matched"
                if reconciliation_records
                and all(
                    record.status == ReconciliationStatus.matched
                    for record in reconciliation_records
                )
                else "manual_review_required"
            ),
            "record_count": len(reconciliation_records),
            "records": [
                {
                    "reconciliation_record_id": record.reconciliation_record_id,
                    "reconciliation_type": record.reconciliation_type.value,
                    "status": record.status.value,
                    "summary": record.summary,
                }
                for record in reconciliation_records
            ],
        }

    def _build_receipt_index(
        self,
        action_intent: ActionIntentRecord,
        kernel_receipt: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "external_receipt_id": kernel_receipt.get("receipt_id"),
            "intent_id": kernel_receipt.get("intent_id"),
            "receipt_type": kernel_receipt.get("receipt_type"),
            "outcome": kernel_receipt.get("outcome"),
            "occurred_at": kernel_receipt.get("occurred_at"),
            "provider_execution_ref": kernel_receipt.get("provider_execution_ref"),
            "action_type": kernel_receipt.get("action_type")
            or action_intent.finance_index.get("action_type"),
            "amount_minor": kernel_receipt.get("amount_minor")
            or action_intent.finance_index.get("amount_minor"),
            "currency": kernel_receipt.get("currency")
            or action_intent.finance_index.get("currency"),
            "source_account_ref": kernel_receipt.get("source_account_ref")
            or action_intent.finance_index.get("source_account_ref"),
            "destination_account_ref": kernel_receipt.get("destination_account_ref")
            or action_intent.finance_index.get("destination_account_ref"),
        }

    def _parse_timestamp(self, raw_value: str) -> datetime:
        normalized = raw_value.replace("Z", "+00:00")
        return normalize_utc(datetime.fromisoformat(normalized))

    def _digest(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _validation_status(self, validation: ContractValidationResult) -> str:
        if not validation.supported:
            return "unsupported"
        if not validation.valid:
            return "invalid"
        return "valid"

    def _check(
        self,
        field: str,
        *,
        expected: Any,
        actual: Any,
        required: bool = True,
    ) -> dict[str, Any]:
        if expected is None and actual is None:
            return {"field": field, "status": "skipped", "expected": expected, "actual": actual}
        if actual is None:
            return {
                "field": field,
                "status": "missing" if required else "not_provided",
                "expected": expected,
                "actual": actual,
            }
        if expected == actual:
            return {"field": field, "status": "matched", "expected": expected, "actual": actual}
        return {"field": field, "status": "mismatch", "expected": expected, "actual": actual}

    def _reconciliation_status(
        self,
        checks: list[dict[str, Any]],
    ) -> ReconciliationStatus:
        statuses = {check["status"] for check in checks}
        if "mismatch" in statuses or "missing" in statuses:
            return ReconciliationStatus.mismatch
        if statuses.issubset({"matched", "skipped"}) and "matched" in statuses:
            return ReconciliationStatus.matched
        return ReconciliationStatus.manual_review_required

    def _reconciliation_summary_text(
        self,
        reconciliation_type: ReconciliationType,
        status: ReconciliationStatus,
        checks: list[dict[str, Any]],
    ) -> str:
        failing_fields = [
            check["field"] for check in checks if check["status"] in {"mismatch", "missing"}
        ]
        if status == ReconciliationStatus.matched:
            return f"{reconciliation_type.value} matched expected finance trace bindings"
        if status == ReconciliationStatus.mismatch:
            return (
                f"{reconciliation_type.value} requires review because fields did not match: "
                + ", ".join(failing_fields)
            )
        return (
            f"{reconciliation_type.value} requires manual review because key comparison "
            "data is incomplete"
        )
