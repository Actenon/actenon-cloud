from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import get_audit_service, get_auth_service, get_current_session
from app.models import (
    AuditEvent,
    ReconciliationRecord,
)
from app.services.audit import (
    ActionTraceNotFoundError,
    AuditEventNotFoundError,
    AuditService,
    ReconciliationRecordNotFoundError,
)
from app.services.auth import (
    TENANT_AUDIT_READ,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_event_id: str
    tenant_id: str
    action_intent_record_id: str | None
    receipt_id: str | None
    issued_proof_id: str | None
    escrow_record_id: str | None
    event_category: str
    event_type: str
    subject_type: str
    subject_id: str
    actor_principal_type: str
    actor_principal_id: str
    event_payload: dict[str, Any]
    created_at: datetime


class ReconciliationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reconciliation_record_id: str
    tenant_id: str
    action_intent_record_id: str
    receipt_id: str
    issued_proof_id: str | None
    escrow_record_id: str | None
    reconciliation_type: str
    status: str
    hook_name: str
    summary: str
    checks: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class TraceActionIntentSummary(BaseModel):
    action_intent_record_id: str
    tenant_id: str
    workflow_key: str
    finance_action_class: str | None
    decision_state: str
    approval_state: str
    evidence_state: str
    execution_state: str
    receipt_state: str
    latest_receipt_id: str | None


class TraceApprovalRequestSummary(BaseModel):
    approval_request_id: str
    status: str
    approval_group_key: str
    required_decision_count: int
    expires_at: datetime | None
    created_at: datetime


class TraceApprovalDecisionSummary(BaseModel):
    approval_decision_id: str
    approval_request_id: str
    decided_by_principal_type: str
    decided_by_principal_id: str
    decision: str
    decision_reason: str | None
    evidence_object_ids: list[str]
    created_at: datetime


class TraceEvidenceSummary(BaseModel):
    evidence_object_id: str
    approval_request_id: str | None
    evidence_type: str
    storage_mode: str
    content_digest: str | None
    status: str
    created_at: datetime


class TraceProofSummary(BaseModel):
    issued_proof_id: str
    status: str
    proof_kind: str
    audience: str
    scope: list[str]
    nonce: str
    action_intent_digest: str
    issued_at: datetime | None
    expires_at: datetime


class TraceEscrowSummary(BaseModel):
    escrow_record_id: str
    issued_proof_id: str
    capability_kind: str
    protected_resource_ref: str
    status: str
    execution_state: str
    provider_execution_ref: str | None
    created_at: datetime


class TraceReceiptSummary(BaseModel):
    receipt_id: str
    issued_proof_id: str | None
    escrow_record_id: str | None
    external_receipt_id: str
    receipt_type: str
    outcome: str
    receipt_timestamp: datetime
    provider_execution_ref: str | None
    receipt_state: str
    created_at: datetime


class FinanceActionTraceResponse(BaseModel):
    generated_at: datetime
    summary: TraceActionIntentSummary
    approvals: list[TraceApprovalRequestSummary]
    approval_decisions: list[TraceApprovalDecisionSummary]
    evidence_objects: list[TraceEvidenceSummary]
    issued_proofs: list[TraceProofSummary]
    escrow_records: list[TraceEscrowSummary]
    receipts: list[TraceReceiptSummary]
    reconciliation_records: list[ReconciliationRecordResponse]
    audit_events: list[AuditEventResponse]


class AuditExportResponse(BaseModel):
    exported_at: datetime
    action_intent_record_id: str
    trace: FinanceActionTraceResponse


def to_audit_event_response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse.model_validate(event, from_attributes=True)


def to_reconciliation_record_response(record: ReconciliationRecord) -> ReconciliationRecordResponse:
    response = ReconciliationRecordResponse.model_validate(record, from_attributes=True)
    response.reconciliation_type = record.reconciliation_type.value
    response.status = record.status.value
    return response


def to_trace_response(trace: dict[str, Any]) -> FinanceActionTraceResponse:
    summary = trace["summary"]
    return FinanceActionTraceResponse(
        generated_at=trace["generated_at"],
        summary=TraceActionIntentSummary(
            action_intent_record_id=summary["action_intent_record_id"],
            tenant_id=summary["tenant_id"],
            workflow_key=summary["workflow_key"],
            finance_action_class=summary["finance_action_class"],
            decision_state=summary["decision_state"].value,
            approval_state=summary["approval_state"].value,
            evidence_state=summary["evidence_state"].value,
            execution_state=summary["execution_state"].value,
            receipt_state=summary["receipt_state"].value,
            latest_receipt_id=summary["latest_receipt_id"],
        ),
        approvals=[
            TraceApprovalRequestSummary(
                approval_request_id=request.approval_request_id,
                status=request.status.value,
                approval_group_key=request.approval_group_key,
                required_decision_count=request.required_decision_count,
                expires_at=request.expires_at,
                created_at=request.created_at,
            )
            for request in trace["approvals"]
        ],
        approval_decisions=[
            TraceApprovalDecisionSummary(
                approval_decision_id=decision.approval_decision_id,
                approval_request_id=decision.approval_request_id,
                decided_by_principal_type=decision.decided_by_principal_type,
                decided_by_principal_id=decision.decided_by_principal_id,
                decision=decision.decision.value,
                decision_reason=decision.decision_reason,
                evidence_object_ids=list(decision.evidence_object_ids),
                created_at=decision.created_at,
            )
            for decision in trace["approval_decisions"]
        ],
        evidence_objects=[
            TraceEvidenceSummary(
                evidence_object_id=evidence.evidence_object_id,
                approval_request_id=evidence.approval_request_id,
                evidence_type=evidence.evidence_type.value,
                storage_mode=evidence.storage_mode.value,
                content_digest=evidence.content_digest,
                status=evidence.status.value,
                created_at=evidence.created_at,
            )
            for evidence in trace["evidence_objects"]
        ],
        issued_proofs=[
            TraceProofSummary(
                issued_proof_id=proof.issued_proof_id,
                status=proof.status.value,
                proof_kind=proof.proof_kind.value,
                audience=proof.audience,
                scope=list(proof.scope),
                nonce=proof.nonce,
                action_intent_digest=proof.action_intent_digest,
                issued_at=proof.issued_at,
                expires_at=proof.expires_at,
            )
            for proof in trace["issued_proofs"]
        ],
        escrow_records=[
            TraceEscrowSummary(
                escrow_record_id=escrow.escrow_record_id,
                issued_proof_id=escrow.issued_proof_id,
                capability_kind=escrow.capability_kind,
                protected_resource_ref=escrow.protected_resource_ref,
                status=escrow.status.value,
                execution_state=escrow.execution_state.value,
                provider_execution_ref=escrow.provider_execution_ref,
                created_at=escrow.created_at,
            )
            for escrow in trace["escrow_records"]
        ],
        receipts=[
            TraceReceiptSummary(
                receipt_id=receipt.receipt_id,
                issued_proof_id=receipt.issued_proof_id,
                escrow_record_id=receipt.escrow_record_id,
                external_receipt_id=receipt.external_receipt_id,
                receipt_type=receipt.receipt_type,
                outcome=receipt.outcome,
                receipt_timestamp=receipt.receipt_timestamp,
                provider_execution_ref=receipt.provider_execution_ref,
                receipt_state=receipt.receipt_state.value,
                created_at=receipt.created_at,
            )
            for receipt in trace["receipts"]
        ],
        reconciliation_records=[
            to_reconciliation_record_response(record)
            for record in trace["reconciliation_records"]
        ],
        audit_events=[to_audit_event_response(event) for event in trace["audit_events"]],
    )


@router.get("/events", response_model=list[AuditEventResponse])
def list_audit_events(
    service: Annotated[AuditService, Depends(get_audit_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    action_intent_record_id: str | None = Query(default=None),
    receipt_id: str | None = Query(default=None),
    subject_type: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
) -> list[AuditEventResponse]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_AUDIT_READ,
        )
        events = service.list_events(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            receipt_id=receipt_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
        )
        return [to_audit_event_response(event) for event in events]
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/events/{audit_event_id}", response_model=AuditEventResponse)
def get_audit_event(
    audit_event_id: str,
    service: Annotated[AuditService, Depends(get_audit_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> AuditEventResponse:
    try:
        event = service.get_event(audit_event_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=event.tenant_id,
            permission=TENANT_AUDIT_READ,
        )
    except AuditEventNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return to_audit_event_response(event)


@router.get("/reconciliation", response_model=list[ReconciliationRecordResponse])
def list_reconciliation_records(
    service: Annotated[AuditService, Depends(get_audit_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    action_intent_record_id: str | None = Query(default=None),
    receipt_id: str | None = Query(default=None),
    reconciliation_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[ReconciliationRecordResponse]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_AUDIT_READ,
        )
        records = service.list_reconciliation_records(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            receipt_id=receipt_id,
            reconciliation_type=reconciliation_type,
            status=status,
        )
        return [to_reconciliation_record_response(record) for record in records]
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get(
    "/reconciliation/{reconciliation_record_id}",
    response_model=ReconciliationRecordResponse,
)
def get_reconciliation_record(
    reconciliation_record_id: str,
    service: Annotated[AuditService, Depends(get_audit_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ReconciliationRecordResponse:
    try:
        record = service.get_reconciliation_record(reconciliation_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_AUDIT_READ,
        )
    except ReconciliationRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return to_reconciliation_record_response(record)


@router.get("/traces/{action_intent_record_id}", response_model=FinanceActionTraceResponse)
def get_action_trace(
    action_intent_record_id: str,
    service: Annotated[AuditService, Depends(get_audit_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> FinanceActionTraceResponse:
    try:
        trace = service.build_action_trace(action_intent_record_id)
        tenant_id = trace["summary"]["tenant_id"]
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_AUDIT_READ,
        )
    except ActionTraceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return to_trace_response(trace)


@router.get("/export", response_model=AuditExportResponse)
def export_action_trace(
    service: Annotated[AuditService, Depends(get_audit_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    action_intent_record_id: str = Query(...),
) -> AuditExportResponse:
    try:
        export_bundle = service.export_action_trace(action_intent_record_id)
        tenant_id = export_bundle["trace"]["summary"]["tenant_id"]
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_AUDIT_READ,
        )
    except ActionTraceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return AuditExportResponse(
        exported_at=export_bundle["exported_at"],
        action_intent_record_id=export_bundle["action_intent_record_id"],
        trace=to_trace_response(export_bundle["trace"]),
    )
