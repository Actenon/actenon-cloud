from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_action_intent_service, get_auth_service, get_current_session
from app.models import (
    ActionIntentRecord,
    ApprovalState,
    ContractValidationStatus,
    DecisionState,
    EvidenceState,
    ExecutionState,
    ReceiptState,
)
from app.services.action_intents import ActionIntentNotFoundError, ActionIntentService
from app.services.auth import (
    TENANT_ACTION_INTENT_READ,
    TENANT_ACTION_INTENT_WRITE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.policy_engine import TenantNotFoundError

router = APIRouter(prefix="/action-intents", tags=["action-intents"])

FinanceActionClass = Literal[
    "payment",
    "transfer",
    "payout",
    "collection",
    "settlement_instruction",
    "other_finance_action",
]


class RequestedBy(BaseModel):
    principal_type: Literal["user", "service_principal", "system"]
    principal_id: str = Field(min_length=1, max_length=255)


class WorkflowBinding(BaseModel):
    policy_pack_id: str | None = None
    workflow_profile: str | None = Field(default=None, max_length=255)
    requested_execution_window: str | None = Field(default=None, max_length=255)


class KernelContractRef(BaseModel):
    contract_family: Literal["action_intent"]
    version_ref: str = Field(min_length=1, max_length=255)


class FinanceRoutingContext(BaseModel):
    action_class: FinanceActionClass | None = None
    amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    source_account_ref: str | None = Field(default=None, max_length=255)
    destination_account_ref: str | None = Field(default=None, max_length=255)
    risk_tier: Literal["low", "medium", "high", "critical"] | None = None


class ActionIntentIntakeRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=32)
    submission_id: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=8, max_length=255)
    requested_by: RequestedBy
    workflow_binding: WorkflowBinding | None = None
    kernel_contract_ref: KernelContractRef
    kernel_action_intent: dict[str, Any]
    finance_routing_context: FinanceRoutingContext | None = None
    evaluation_context: dict[str, Any] = Field(default_factory=dict)
    client_tags: list[str] = Field(default_factory=list)
    external_reference: str | None = Field(default=None, max_length=255)


class ActionIntentIntakeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_intent_record_id: str
    tenant_id: str
    policy_id: str | None
    policy_version: int | None
    submission_id: str
    idempotency_key: str
    requested_by_principal_type: str
    requested_by_principal_id: str
    workflow_key: str
    external_action_intent_id: str | None
    external_reference: str | None
    contract_family: str
    contract_version_ref: str
    contract_validation_status: ContractValidationStatus
    contract_validation_errors: list[str]
    action_intent_digest: str
    decision_state: DecisionState
    decision_reason: str
    matched_rule_id: str | None
    approval_state: ApprovalState
    evidence_state: EvidenceState
    execution_state: ExecutionState
    receipt_state: ReceiptState
    latest_receipt_id: str | None
    approval_requirement: dict[str, Any] | None
    evidence_requirement: dict[str, Any] | None
    workflow_binding: dict[str, Any] | None
    finance_routing_context: dict[str, Any] | None
    finance_action_class: str | None
    finance_index: dict[str, Any]
    action_intent_payload: dict[str, Any]
    evaluation_context: dict[str, Any]
    evaluation_trace: list[dict[str, Any]]
    client_tags: list[str]
    created_at: datetime
    updated_at: datetime
    idempotent_replay: bool = False


class ActionIntentListItemResponse(BaseModel):
    action_intent_record_id: str
    tenant_id: str
    submission_id: str
    workflow_key: str
    external_action_intent_id: str | None
    external_reference: str | None
    requested_by_principal_type: str
    requested_by_principal_id: str
    finance_action_class: str | None
    amount_minor: int | None
    currency: str | None
    source_account_ref: str | None
    destination_account_ref: str | None
    destination_country: str | None
    decision_state: DecisionState
    decision_reason: str
    approval_state: ApprovalState
    evidence_state: EvidenceState
    execution_state: ExecutionState
    receipt_state: ReceiptState
    latest_receipt_id: str | None
    created_at: datetime
    updated_at: datetime


def to_action_intent_response(
    record: ActionIntentRecord,
    *,
    idempotent_replay: bool,
) -> ActionIntentIntakeResponse:
    response = ActionIntentIntakeResponse.model_validate(record, from_attributes=True)
    response.idempotent_replay = idempotent_replay
    return response


def to_action_intent_list_item(record: ActionIntentRecord) -> ActionIntentListItemResponse:
    finance_index = record.finance_index or {}
    return ActionIntentListItemResponse(
        action_intent_record_id=record.action_intent_record_id,
        tenant_id=record.tenant_id,
        submission_id=record.submission_id,
        workflow_key=record.workflow_key,
        external_action_intent_id=record.external_action_intent_id,
        external_reference=record.external_reference,
        requested_by_principal_type=record.requested_by_principal_type,
        requested_by_principal_id=record.requested_by_principal_id,
        finance_action_class=record.finance_action_class,
        amount_minor=finance_index.get("amount_minor"),
        currency=finance_index.get("currency"),
        source_account_ref=finance_index.get("source_account_ref"),
        destination_account_ref=finance_index.get("destination_account_ref"),
        destination_country=finance_index.get("destination_country"),
        decision_state=record.decision_state,
        decision_reason=record.decision_reason,
        approval_state=record.approval_state,
        evidence_state=record.evidence_state,
        execution_state=record.execution_state,
        receipt_state=record.receipt_state,
        latest_receipt_id=record.latest_receipt_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=list[ActionIntentListItemResponse])
def list_action_intents(
    service: Annotated[ActionIntentService, Depends(get_action_intent_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    workflow_key: str | None = Query(default=None),
    decision_state: DecisionState | None = Query(default=None),
    approval_state: ApprovalState | None = Query(default=None),
    evidence_state: EvidenceState | None = Query(default=None),
    execution_state: ExecutionState | None = Query(default=None),
    receipt_state: ReceiptState | None = Query(default=None),
    external_reference: str | None = Query(default=None),
) -> list[ActionIntentListItemResponse]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_ACTION_INTENT_READ,
        )
        records = service.list_records(
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            decision_state=decision_state,
            approval_state=approval_state,
            evidence_state=evidence_state,
            execution_state=execution_state,
            receipt_state=receipt_state,
            external_reference=external_reference,
        )
        return [to_action_intent_list_item(record) for record in records]
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("", response_model=ActionIntentIntakeResponse, status_code=status.HTTP_201_CREATED)
def intake_action_intent(
    payload: ActionIntentIntakeRequest,
    response: Response,
    service: Annotated[ActionIntentService, Depends(get_action_intent_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ActionIntentIntakeResponse:
    try:
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=payload.tenant_id,
            permission=TENANT_ACTION_INTENT_WRITE,
        )
        result = service.intake(payload.model_dump(mode="json"))
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if result.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    return to_action_intent_response(result.record, idempotent_replay=result.idempotent_replay)


@router.get("/{action_intent_record_id}", response_model=ActionIntentIntakeResponse)
def get_action_intent(
    action_intent_record_id: str,
    service: Annotated[ActionIntentService, Depends(get_action_intent_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ActionIntentIntakeResponse:
    try:
        record = service.get_record(action_intent_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_ACTION_INTENT_READ,
        )
    except ActionIntentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_action_intent_response(record, idempotent_replay=False)
