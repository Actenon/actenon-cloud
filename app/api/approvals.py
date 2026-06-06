from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_approval_service, get_auth_service, get_current_session
from app.models import (
    ApprovalAssignmentStatus,
    ApprovalDecisionType,
    ApprovalRequest,
    ApprovalRequestStatus,
)
from app.services.approvals import (
    ApprovalActor,
    ApprovalAuthorizationError,
    ApprovalDecisionStateError,
    ApprovalRequestNotFoundError,
    ApprovalService,
    ApprovalValidationError,
)
from app.services.auth import (
    TENANT_APPROVAL_READ,
    TENANT_APPROVAL_WRITE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_assignment_id: str
    principal_type: str
    principal_id: str
    assignment_status: ApprovalAssignmentStatus
    assigned_at: datetime
    acted_at: datetime | None


class ApprovalDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_decision_id: str
    decided_by_principal_type: str
    decided_by_principal_id: str
    decision: ApprovalDecisionType
    decision_reason: str | None
    evidence_object_ids: list[str]
    created_at: datetime


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_request_id: str
    tenant_id: str
    action_intent_record_id: str
    policy_id: str | None
    workflow_rule_id: str | None
    approval_group_key: str
    required_decision_count: int
    eligible_role_ids: list[str]
    separation_of_duties: dict[str, bool]
    status: ApprovalRequestStatus
    decision_reason: str | None
    expires_at: datetime | None
    satisfied_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime
    assignments: list[ApprovalAssignmentResponse]
    decisions: list[ApprovalDecisionResponse]


class ApprovalDecisionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision: ApprovalDecisionType
    decision_reason: str | None = Field(default=None, max_length=2_000)
    evidence_object_ids: list[str] = Field(default_factory=list)


@router.get("", response_model=list[ApprovalRequestResponse])
def list_approval_requests(
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    action_intent_record_id: str | None = Query(default=None),
    status_filter: ApprovalRequestStatus | None = Query(default=None, alias="status"),
) -> list[ApprovalRequest]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_APPROVAL_READ,
        )
        return service.list_requests(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            status=status_filter,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{approval_request_id}", response_model=ApprovalRequestResponse)
def get_approval_request(
    approval_request_id: str,
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ApprovalRequest:
    try:
        request = service.get_request(approval_request_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=request.tenant_id,
            permission=TENANT_APPROVAL_READ,
        )
        return request
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/{approval_request_id}/decisions",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_approval_decision(
    approval_request_id: str,
    payload: ApprovalDecisionCreateRequest,
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ApprovalRequest:
    try:
        approval_request = service.get_request(approval_request_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=approval_request.tenant_id,
            permission=TENANT_APPROVAL_WRITE,
        )
        submission = service.record_decision(
            approval_request_id,
            actor=ApprovalActor(
                principal_type=auth_session.principal_type,
                principal_id=auth_session.principal_id,
                claimed_role_ids=auth_service.tenant_role_ids_for_session(
                    auth_session,
                    tenant_id=approval_request.tenant_id,
                ),
            ),
            decision=payload.decision,
            decision_reason=payload.decision_reason,
            evidence_object_ids=payload.evidence_object_ids,
        )
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApprovalAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ApprovalDecisionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ApprovalValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return submission.request
