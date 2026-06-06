from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.dependencies import (
    get_auth_service,
    get_current_session,
    get_policy_management_service,
)
from app.models import DecisionState, EvidenceType, Policy, PolicyStatus
from app.services.auth import (
    TENANT_POLICY_READ,
    TENANT_POLICY_WRITE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.policy_engine import (
    PolicyManagementService,
    PolicyNotFoundError,
    PolicyStateError,
    TenantNotFoundError,
)

router = APIRouter(prefix="/policies", tags=["policies"])

ConditionSource = Literal["action_intent", "context", "intake"]
ConditionOperator = Literal[
    "equals",
    "not_equals",
    "gte",
    "gt",
    "lte",
    "lt",
    "in",
    "contains",
    "exists",
]


class PolicyCondition(BaseModel):
    source: ConditionSource
    field: str = Field(min_length=1, max_length=255)
    operator: ConditionOperator
    value: Any | None = None

    @field_validator("value")
    @classmethod
    def validate_exists_operator(cls, value: Any | None, info) -> Any | None:
        if (
            info.data.get("operator") == "exists"
            and value is not None
            and not isinstance(value, bool)
        ):
            raise ValueError("exists operator accepts only boolean values")
        return value


class PolicyRule(BaseModel):
    rule_id: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    priority: int = Field(default=100, ge=0, le=10_000)
    decision: DecisionState
    all_conditions: list[PolicyCondition] = Field(min_length=1)
    approval_requirement: ApprovalRequirement | None = None
    evidence_requirement: EvidenceRequirement | None = None

    @field_validator("decision")
    @classmethod
    def validate_policy_decision(cls, value: DecisionState) -> DecisionState:
        if value == DecisionState.structurally_non_executable:
            raise ValueError("structurally_non_executable is reserved for hard rules")
        return value


class ApprovalRequirement(BaseModel):
    required_decision_count: int = Field(default=1, ge=1, le=10)
    eligible_principal_ids: list[str] = Field(default_factory=list)
    eligible_role_ids: list[str] = Field(default_factory=list)
    approval_group_key: str | None = Field(default=None, max_length=255)
    expires_in_seconds: int | None = Field(default=None, ge=1, le=604_800)
    require_requester_separation: bool = True
    require_distinct_approvers: bool = True


class EvidenceRequirement(BaseModel):
    minimum_count: int = Field(default=1, ge=1, le=25)
    allowed_evidence_types: list[EvidenceType] = Field(default_factory=list)
    expires_in_seconds: int | None = Field(default=None, ge=1, le=2_592_000)


class PolicyCreateRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    workflow_key: str = Field(min_length=1, max_length=255)
    finance_action_classes: list[str] = Field(min_length=1)
    default_decision: DecisionState
    rules: list[PolicyRule] = Field(default_factory=list)

    @field_validator("default_decision")
    @classmethod
    def validate_default_decision(cls, value: DecisionState) -> DecisionState:
        if value == DecisionState.structurally_non_executable:
            raise ValueError("structurally_non_executable is reserved for hard rules")
        return value


class PolicyUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    finance_action_classes: list[str] = Field(min_length=1)
    default_decision: DecisionState
    rules: list[PolicyRule] = Field(default_factory=list)

    @field_validator("default_decision")
    @classmethod
    def validate_default_decision(cls, value: DecisionState) -> DecisionState:
        if value == DecisionState.structurally_non_executable:
            raise ValueError("structurally_non_executable is reserved for hard rules")
        return value


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_id: str
    tenant_id: str
    name: str
    description: str | None
    workflow_key: str
    version: int
    status: PolicyStatus
    default_decision: DecisionState
    finance_action_classes: list[str]
    rules: list[dict[str, Any]]
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreateRequest,
    service: Annotated[PolicyManagementService, Depends(get_policy_management_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> Policy:
    try:
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=payload.tenant_id,
            permission=TENANT_POLICY_WRITE,
        )
        return service.create_policy(
            tenant_id=payload.tenant_id,
            name=payload.name,
            description=payload.description,
            workflow_key=payload.workflow_key,
            default_decision=payload.default_decision,
            finance_action_classes=payload.finance_action_classes,
            rules=[rule.model_dump(mode="json") for rule in payload.rules],
        )
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("", response_model=list[PolicyResponse])
def list_policies(
    service: Annotated[PolicyManagementService, Depends(get_policy_management_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    workflow_key: str | None = Query(default=None),
    status_filter: PolicyStatus | None = Query(default=None, alias="status"),
) -> list[Policy]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_POLICY_READ,
        )
        return service.list_policies(
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            status=status_filter,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: str,
    service: Annotated[PolicyManagementService, Depends(get_policy_management_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> Policy:
    try:
        policy = service.get_policy(policy_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=policy.tenant_id,
            permission=TENANT_POLICY_READ,
        )
        return policy
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: str,
    payload: PolicyUpdateRequest,
    service: Annotated[PolicyManagementService, Depends(get_policy_management_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> Policy:
    try:
        policy = service.get_policy(policy_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=policy.tenant_id,
            permission=TENANT_POLICY_WRITE,
        )
        return service.update_policy(
            policy_id,
            name=payload.name,
            description=payload.description,
            default_decision=payload.default_decision,
            finance_action_classes=payload.finance_action_classes,
            rules=[rule.model_dump(mode="json") for rule in payload.rules],
        )
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PolicyStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{policy_id}/activate", response_model=PolicyResponse)
def activate_policy(
    policy_id: str,
    service: Annotated[PolicyManagementService, Depends(get_policy_management_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> Policy:
    try:
        policy = service.get_policy(policy_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=policy.tenant_id,
            permission=TENANT_POLICY_WRITE,
        )
        return service.activate_policy(policy_id)
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PolicyStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
