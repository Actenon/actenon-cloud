from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from jsonschema import Draft202012Validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.metrics import get_metrics_registry
from app.models import (
    ActionIntentRecord,
    ApprovalState,
    ContractValidationStatus,
    DecisionState,
    EvidenceState,
    ExecutionState,
    ReceiptState,
    TenantStatus,
)
from app.services.approvals import ApprovalService
from app.services.evidence import EvidenceService
from app.services.policy_engine import PolicyEngine, PolicyManagementService

if TYPE_CHECKING:
    from app.services.auth import AuthenticatedSession

SUPPORTED_ACTION_INTENT_CONTRACTS = {
    "open_execution_kernel.action_intent.finance.v1alpha1": (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "kernel"
        / "action_intent.finance.v1alpha1.schema.json"
    )
}
workflow_logger = logging.getLogger("action_control_plane.workflow")


class ActionIntentNotFoundError(LookupError):
    pass


@dataclass(slots=True)
class ContractValidationResult:
    supported: bool
    valid: bool
    errors: list[str]


@dataclass(slots=True)
class IntakeResult:
    record: ActionIntentRecord
    idempotent_replay: bool


@lru_cache
def _validator_for_version(version_ref: str) -> Draft202012Validator | None:
    schema_path = SUPPORTED_ACTION_INTENT_CONTRACTS.get(version_ref)
    if schema_path is None:
        return None
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


class KernelContractRegistry:
    def validate_action_intent(
        self,
        *,
        contract_family: str,
        version_ref: str,
        payload: dict[str, Any],
    ) -> ContractValidationResult:
        if contract_family != "action_intent":
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
            if location:
                formatted_errors.append(f"{location}: {error.message}")
            else:
                formatted_errors.append(error.message)
        return ContractValidationResult(supported=True, valid=False, errors=formatted_errors)

class ActionIntentService:
    def __init__(
        self,
        session: Session,
        *,
        contract_registry: KernelContractRegistry,
        policy_service: PolicyManagementService,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalService | None = None,
        evidence_service: EvidenceService | None = None,
    ) -> None:
        self.session = session
        self.contract_registry = contract_registry
        self.policy_service = policy_service
        self.policy_engine = policy_engine or PolicyEngine()
        self.approval_service = approval_service or ApprovalService(session)
        self.evidence_service = evidence_service

    def intake(
        self,
        payload: dict[str, Any],
        *,
        auth_session: AuthenticatedSession | None = None,
    ) -> IntakeResult:
        started = perf_counter()
        # B5: bind requested_by to the authenticated session. The client
        # may still send a ``requested_by`` in the request body for schema
        # compatibility, but the authoritative principal is the one bound
        # to the bearer token — never the client-supplied value.
        if auth_session is not None:
            payload["requested_by"] = {
                "principal_type": auth_session.principal_type,
                "principal_id": auth_session.principal_id,
            }
        requested_by = payload.get("requested_by") or {}
        intake_counter = get_metrics_registry().counter(
            "action_control_plane_action_intake_total",
            "Action Intent intake results by control decision and contract status.",
            label_names=("decision_state", "contract_validation_status", "idempotent_replay"),
        )

        try:
            tenant = self.policy_service.get_tenant(payload["tenant_id"])
            if tenant.status != TenantStatus.active:
                raise ValueError("tenant is not active")

            existing = self.session.scalar(
                select(ActionIntentRecord).where(
                    ActionIntentRecord.tenant_id == payload["tenant_id"],
                    ActionIntentRecord.idempotency_key == payload["idempotency_key"],
                )
            )
            if existing is not None:
                self._synchronize_record(existing)
                duration_ms = int((perf_counter() - started) * 1000)
                intake_counter.inc(
                    decision_state=existing.decision_state.value,
                    contract_validation_status=existing.contract_validation_status.value,
                    idempotent_replay="true",
                )
                workflow_logger.info(
                    "action_intent.intake.replayed",
                    extra={
                        "event": "action_intent.intake.replayed",
                        "tenant_id": existing.tenant_id,
                        "principal_type": existing.requested_by_principal_type,
                        "principal_id": existing.requested_by_principal_id,
                        "action_intent_record_id": existing.action_intent_record_id,
                        "decision_state": existing.decision_state.value,
                        "approval_state": existing.approval_state.value,
                        "evidence_state": existing.evidence_state.value,
                        "contract_validation_status": existing.contract_validation_status.value,
                        "outcome": existing.decision_state.value,
                        "idempotent_replay": True,
                        "duration_ms": duration_ms,
                    },
                )
                return IntakeResult(record=existing, idempotent_replay=True)

            contract_ref = payload["kernel_contract_ref"]
            action_intent = payload["kernel_action_intent"]
            validation = self.contract_registry.validate_action_intent(
                contract_family=contract_ref["contract_family"],
                version_ref=contract_ref["version_ref"],
                payload=action_intent,
            )

            workflow_binding = payload.get("workflow_binding") or {}
            finance_routing_context = payload.get("finance_routing_context") or {}
            workflow_key = (
                action_intent.get("workflow_key")
                or workflow_binding.get("workflow_profile")
                or "unknown"
            )
            finance_action_class = action_intent.get("action_type") or finance_routing_context.get(
                "action_class"
            )
            intake_context = self._build_intake_context(
                payload=payload,
                workflow_key=workflow_key,
                finance_action_class=finance_action_class,
            )
            policy = self.policy_service.get_active_policy(payload["tenant_id"], workflow_key)
            decision = self.policy_engine.evaluate(
                action_intent=action_intent,
                intake_context=intake_context,
                evaluation_context=payload.get("evaluation_context", {}),
                policy=policy,
                contract_supported=validation.supported,
                contract_valid=validation.valid,
                contract_errors=validation.errors,
            )

            record = ActionIntentRecord(
                action_intent_record_id=uuid4().hex,
                tenant_id=payload["tenant_id"],
                policy_id=decision.policy.policy_id if decision.policy else None,
                policy_version=decision.policy.version if decision.policy else None,
                submission_id=payload["submission_id"],
                idempotency_key=payload["idempotency_key"],
                requested_by_principal_type=payload["requested_by"]["principal_type"],
                requested_by_principal_id=payload["requested_by"]["principal_id"],
                workflow_key=workflow_key,
                external_action_intent_id=action_intent.get("intent_id"),
                contract_family=contract_ref["contract_family"],
                contract_version_ref=contract_ref["version_ref"],
                contract_validation_status=self._validation_status(validation),
                contract_validation_errors=validation.errors,
                action_intent_digest=self._digest(action_intent),
                action_intent_payload=action_intent,
                workflow_binding=workflow_binding or None,
                finance_routing_context=finance_routing_context or None,
                finance_action_class=finance_action_class,
                finance_index=self._build_finance_index(
                    action_intent,
                    payload.get("evaluation_context", {}),
                ),
                evaluation_context=payload.get("evaluation_context", {}),
                client_tags=payload.get("client_tags", []),
                external_reference=payload.get("external_reference"),
                approval_state=(
                    ApprovalState.not_started
                    if decision.approval_requirement
                    else ApprovalState.not_required
                ),
                evidence_state=(
                    EvidenceState.pending
                    if decision.evidence_requirement
                    else EvidenceState.not_required
                ),
                execution_state=ExecutionState.not_requested,
                receipt_state=ReceiptState.none,
                latest_receipt_id=None,
                approval_requirement=decision.approval_requirement,
                evidence_requirement=decision.evidence_requirement,
                decision_state=decision.state,
                decision_reason=decision.reason,
                matched_rule_id=decision.matched_rule_id,
                evaluation_trace=decision.trace,
            )
            self.session.add(record)
            self.session.flush()
            self.approval_service.initialize_for_action_intent(record)
            if self.evidence_service is not None:
                self.evidence_service.initialize_for_action_intent(record)
            self.session.commit()
            self.session.refresh(record)

            duration_ms = int((perf_counter() - started) * 1000)
            intake_counter.inc(
                decision_state=record.decision_state.value,
                contract_validation_status=record.contract_validation_status.value,
                idempotent_replay="false",
            )
            workflow_logger.info(
                "action_intent.intake.completed",
                extra={
                    "event": "action_intent.intake.completed",
                    "tenant_id": record.tenant_id,
                    "principal_type": record.requested_by_principal_type,
                    "principal_id": record.requested_by_principal_id,
                    "action_intent_record_id": record.action_intent_record_id,
                    "decision_state": record.decision_state.value,
                    "approval_state": record.approval_state.value,
                    "evidence_state": record.evidence_state.value,
                    "execution_state": record.execution_state.value,
                    "receipt_state": record.receipt_state.value,
                    "contract_validation_status": record.contract_validation_status.value,
                    "outcome": record.decision_state.value,
                    "idempotent_replay": False,
                    "duration_ms": duration_ms,
                },
            )
            return IntakeResult(record=record, idempotent_replay=False)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            intake_counter.inc(
                decision_state="error",
                contract_validation_status="unknown",
                idempotent_replay="false",
            )
            log_method = (
                workflow_logger.warning
                if isinstance(exc, ValueError)
                else workflow_logger.exception
            )
            log_method(
                "action_intent.intake.failed",
                extra={
                    "event": "action_intent.intake.failed",
                    "tenant_id": payload.get("tenant_id"),
                    "principal_type": requested_by.get("principal_type"),
                    "principal_id": requested_by.get("principal_id"),
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            raise

    def get_record(self, action_intent_record_id: str) -> ActionIntentRecord:
        record = self.session.get(ActionIntentRecord, action_intent_record_id)
        if record is None:
            raise ActionIntentNotFoundError(
                f"action intent record '{action_intent_record_id}' was not found"
            )
        self._synchronize_record(record)
        return record

    def list_records(
        self,
        *,
        tenant_id: str | None = None,
        workflow_key: str | None = None,
        decision_state: DecisionState | None = None,
        approval_state: ApprovalState | None = None,
        evidence_state: EvidenceState | None = None,
        execution_state: ExecutionState | None = None,
        receipt_state: ReceiptState | None = None,
        external_reference: str | None = None,
    ) -> list[ActionIntentRecord]:
        query = select(ActionIntentRecord)
        if tenant_id is not None:
            query = query.where(ActionIntentRecord.tenant_id == tenant_id)
        if workflow_key is not None:
            query = query.where(ActionIntentRecord.workflow_key == workflow_key)
        if decision_state is not None:
            query = query.where(ActionIntentRecord.decision_state == decision_state)
        if approval_state is not None:
            query = query.where(ActionIntentRecord.approval_state == approval_state)
        if evidence_state is not None:
            query = query.where(ActionIntentRecord.evidence_state == evidence_state)
        if execution_state is not None:
            query = query.where(ActionIntentRecord.execution_state == execution_state)
        if receipt_state is not None:
            query = query.where(ActionIntentRecord.receipt_state == receipt_state)
        if external_reference is not None:
            query = query.where(ActionIntentRecord.external_reference == external_reference)
        query = query.order_by(
            ActionIntentRecord.updated_at.desc(),
            ActionIntentRecord.created_at.desc(),
        )
        records = list(self.session.scalars(query))
        for record in records:
            self._synchronize_record(record)
        return records

    def _build_intake_context(
        self,
        *,
        payload: dict[str, Any],
        workflow_key: str,
        finance_action_class: str | None,
    ) -> dict[str, Any]:
        workflow_binding = payload.get("workflow_binding") or {}
        finance_routing_context = payload.get("finance_routing_context") or {}
        action_intent = payload["kernel_action_intent"]
        return {
            "tenant_id": payload["tenant_id"],
            "submission_id": payload["submission_id"],
            "requested_by": payload["requested_by"],
            "workflow_key": workflow_key,
            "workflow_mismatch": bool(
                workflow_binding.get("workflow_profile")
                and action_intent.get("workflow_key")
                and workflow_binding["workflow_profile"] != action_intent["workflow_key"]
            ),
            "routing_mismatch": bool(
                finance_routing_context.get("action_class")
                and action_intent.get("action_type")
                and finance_routing_context["action_class"] != action_intent["action_type"]
            ),
            "finance_action_class": finance_action_class,
        }

    def _build_finance_index(
        self,
        action_intent: dict[str, Any],
        evaluation_context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "workflow_key": action_intent.get("workflow_key"),
            "action_type": action_intent.get("action_type"),
            "amount_minor": action_intent.get("amount_minor"),
            "currency": action_intent.get("currency"),
            "source_account_ref": action_intent.get("source_account_ref"),
            "destination_account_ref": action_intent.get("destination_account_ref"),
            "destination_country": action_intent.get("destination_country"),
            "risk_tier": evaluation_context.get("risk_tier"),
        }

    def _digest(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _validation_status(self, validation: ContractValidationResult) -> ContractValidationStatus:
        if not validation.supported:
            return ContractValidationStatus.unsupported
        if not validation.valid:
            return ContractValidationStatus.invalid
        return ContractValidationStatus.valid

    def _synchronize_record(self, record: ActionIntentRecord) -> None:
        self.approval_service.synchronize_action_intent_state(record)
        if self.evidence_service is not None:
            self.evidence_service.synchronize_action_intent_state(record)
        if self.session.dirty:
            self.session.commit()
            self.session.refresh(record)
