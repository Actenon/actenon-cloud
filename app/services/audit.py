from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ActionIntentRecord,
    ApprovalDecision,
    ApprovalRequest,
    AuditEvent,
    EscrowRecord,
    EvidenceObject,
    IssuedProof,
    ReceiptRecord,
    ReconciliationRecord,
)


class AuditEventNotFoundError(LookupError):
    pass


class ReconciliationRecordNotFoundError(LookupError):
    pass


class ActionTraceNotFoundError(LookupError):
    pass


@dataclass(slots=True)
class AuditActor:
    principal_type: str
    principal_id: str


def utc_now() -> datetime:
    return datetime.now(UTC)


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record_event(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str | None,
        receipt_id: str | None,
        issued_proof_id: str | None,
        escrow_record_id: str | None,
        event_category: str,
        event_type: str,
        subject_type: str,
        subject_id: str,
        actor: AuditActor,
        event_payload: dict[str, Any],
    ) -> AuditEvent:
        event = AuditEvent(
            audit_event_id=uuid4().hex,
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            receipt_id=receipt_id,
            issued_proof_id=issued_proof_id,
            escrow_record_id=escrow_record_id,
            event_category=event_category,
            event_type=event_type,
            subject_type=subject_type,
            subject_id=subject_id,
            actor_principal_type=actor.principal_type,
            actor_principal_id=actor.principal_id,
            event_payload=event_payload,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_events(
        self,
        *,
        tenant_id: str | None = None,
        action_intent_record_id: str | None = None,
        receipt_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        query = select(AuditEvent).order_by(AuditEvent.created_at.asc())
        if tenant_id is not None:
            query = query.where(AuditEvent.tenant_id == tenant_id)
        if action_intent_record_id is not None:
            query = query.where(AuditEvent.action_intent_record_id == action_intent_record_id)
        if receipt_id is not None:
            query = query.where(AuditEvent.receipt_id == receipt_id)
        if subject_type is not None:
            query = query.where(AuditEvent.subject_type == subject_type)
        if subject_id is not None:
            query = query.where(AuditEvent.subject_id == subject_id)
        if event_type is not None:
            query = query.where(AuditEvent.event_type == event_type)
        return list(self.session.scalars(query))

    def get_event(self, audit_event_id: str) -> AuditEvent:
        event = self.session.get(AuditEvent, audit_event_id)
        if event is None:
            raise AuditEventNotFoundError(f"audit event '{audit_event_id}' was not found")
        return event

    def list_reconciliation_records(
        self,
        *,
        tenant_id: str | None = None,
        action_intent_record_id: str | None = None,
        receipt_id: str | None = None,
        reconciliation_type: str | None = None,
        status: str | None = None,
    ) -> list[ReconciliationRecord]:
        query = select(ReconciliationRecord).order_by(ReconciliationRecord.created_at.asc())
        if tenant_id is not None:
            query = query.where(ReconciliationRecord.tenant_id == tenant_id)
        if action_intent_record_id is not None:
            query = query.where(
                ReconciliationRecord.action_intent_record_id == action_intent_record_id
            )
        if receipt_id is not None:
            query = query.where(ReconciliationRecord.receipt_id == receipt_id)
        if reconciliation_type is not None:
            query = query.where(
                ReconciliationRecord.reconciliation_type == reconciliation_type
            )
        if status is not None:
            query = query.where(ReconciliationRecord.status == status)
        return list(self.session.scalars(query))

    def get_reconciliation_record(self, reconciliation_record_id: str) -> ReconciliationRecord:
        record = self.session.get(ReconciliationRecord, reconciliation_record_id)
        if record is None:
            raise ReconciliationRecordNotFoundError(
                f"reconciliation record '{reconciliation_record_id}' was not found"
            )
        return record

    def build_action_trace(self, action_intent_record_id: str) -> dict[str, Any]:
        action_intent = self.session.get(ActionIntentRecord, action_intent_record_id)
        if action_intent is None:
            raise ActionTraceNotFoundError(
                f"action intent record '{action_intent_record_id}' was not found"
            )

        approvals = list(
            self.session.scalars(
                select(ApprovalRequest)
                .where(ApprovalRequest.action_intent_record_id == action_intent_record_id)
                .order_by(ApprovalRequest.created_at.asc())
            )
        )
        approval_request_ids = [request.approval_request_id for request in approvals]
        decisions = list(
            self.session.scalars(
                select(ApprovalDecision)
                .where(ApprovalDecision.approval_request_id.in_(approval_request_ids))
                .order_by(ApprovalDecision.created_at.asc())
            )
        ) if approval_request_ids else []
        evidence_objects = list(
            self.session.scalars(
                select(EvidenceObject)
                .where(EvidenceObject.action_intent_record_id == action_intent_record_id)
                .order_by(EvidenceObject.created_at.asc())
            )
        )
        proofs = list(
            self.session.scalars(
                select(IssuedProof)
                .where(IssuedProof.action_intent_record_id == action_intent_record_id)
                .order_by(IssuedProof.created_at.asc())
            )
        )
        escrow_records = list(
            self.session.scalars(
                select(EscrowRecord)
                .where(EscrowRecord.action_intent_record_id == action_intent_record_id)
                .order_by(EscrowRecord.created_at.asc())
            )
        )
        receipts = list(
            self.session.scalars(
                select(ReceiptRecord)
                .where(ReceiptRecord.action_intent_record_id == action_intent_record_id)
                .order_by(ReceiptRecord.receipt_timestamp.asc())
            )
        )
        reconciliation_records = list(
            self.session.scalars(
                select(ReconciliationRecord)
                .where(ReconciliationRecord.action_intent_record_id == action_intent_record_id)
                .order_by(ReconciliationRecord.created_at.asc())
            )
        )
        audit_events = self.list_events(action_intent_record_id=action_intent_record_id)

        return {
            "generated_at": utc_now(),
            "summary": {
                "tenant_id": action_intent.tenant_id,
                "action_intent_record_id": action_intent.action_intent_record_id,
                "workflow_key": action_intent.workflow_key,
                "finance_action_class": action_intent.finance_action_class,
                "decision_state": action_intent.decision_state,
                "approval_state": action_intent.approval_state,
                "evidence_state": action_intent.evidence_state,
                "execution_state": action_intent.execution_state,
                "receipt_state": action_intent.receipt_state,
                "latest_receipt_id": action_intent.latest_receipt_id,
            },
            "action_intent": action_intent,
            "approvals": approvals,
            "approval_decisions": decisions,
            "evidence_objects": evidence_objects,
            "issued_proofs": proofs,
            "escrow_records": escrow_records,
            "receipts": receipts,
            "reconciliation_records": reconciliation_records,
            "audit_events": audit_events,
        }

    def export_action_trace(self, action_intent_record_id: str) -> dict[str, Any]:
        trace = self.build_action_trace(action_intent_record_id)
        return {
            "exported_at": utc_now(),
            "action_intent_record_id": action_intent_record_id,
            "trace": trace,
        }
