from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import (
    get_auth_service,
    get_current_session,
    get_escrow_service,
    get_issuance_service,
)
from app.models import (
    CapabilityReleaseMode,
    EscrowRecord,
    EscrowStatus,
    EscrowTransitionType,
    ExecutionState,
)
from app.services.auth import (
    TENANT_ESCROW_READ,
    TENANT_ESCROW_WRITE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.escrow import (
    CapabilityReleaseNotAvailableError,
    CapabilityTokenValidationError,
    EscrowActor,
    EscrowCreateResult,
    EscrowRecordNotFoundError,
    EscrowReleaseResult,
    EscrowService,
    EscrowStateError,
    EscrowValidationError,
)
from app.services.issuance import IssuanceService, IssuedProofNotFoundError

router = APIRouter(prefix="/escrow", tags=["escrow"])


class EscrowActorPayload(BaseModel):
    principal_type: Literal["user", "service_principal", "system"]
    principal_id: str = Field(min_length=1, max_length=255)


class EscrowTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    escrow_transition_record_id: str
    transition_type: EscrowTransitionType
    from_status: EscrowStatus | None
    to_status: EscrowStatus
    from_execution_state: ExecutionState | None
    to_execution_state: ExecutionState
    actor_principal_type: str
    actor_principal_id: str
    reason_code: str | None
    reason_detail: str | None
    transition_metadata: dict[str, Any]
    created_at: datetime


class EscrowRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    escrow_record_id: str
    tenant_id: str
    action_intent_record_id: str
    issued_proof_id: str
    capability_kind: str
    protected_resource_ref: str
    release_mode: CapabilityReleaseMode
    status: EscrowStatus
    execution_state: ExecutionState
    audience: str
    scope: list[str]
    scope_hash: str
    action_intent_digest: str
    proof_nonce: str
    created_by_principal_type: str
    created_by_principal_id: str
    capability_reference: str | None
    capability_metadata: dict[str, Any]
    release_metadata: dict[str, Any]
    provider_execution_ref: str | None
    provider_status: str | None
    failure_reason: str | None
    revocation_reason_code: str | None
    revocation_reason_detail: str | None
    quarantine_reason_code: str | None
    quarantine_reason_detail: str | None
    released_at: datetime | None
    consumed_at: datetime | None
    revoked_at: datetime | None
    quarantined_at: datetime | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    transitions: list[EscrowTransitionResponse]
    idempotent_replay: bool = False


class CapabilityReleaseResponse(EscrowRecordResponse):
    capability_token: str


class EscrowHoldRequest(BaseModel):
    issued_proof_id: str = Field(min_length=1, max_length=32)
    capability_kind: str = Field(min_length=1, max_length=255)
    protected_resource_ref: str = Field(min_length=1, max_length=1024)
    requested_by: EscrowActorPayload
    expires_in_seconds: int | None = Field(default=None, ge=60, le=604800)
    capability_metadata: dict[str, Any] = Field(default_factory=dict)


class EscrowReleaseRequest(BaseModel):
    released_by: EscrowActorPayload


class EscrowConsumeRequest(BaseModel):
    capability_token: str = Field(min_length=16)
    consumed_by: EscrowActorPayload
    provider_execution_ref: str | None = Field(default=None, max_length=255)
    provider_status: str | None = Field(default=None, max_length=255)
    transition_metadata: dict[str, Any] = Field(default_factory=dict)


class EscrowInterventionRequest(BaseModel):
    acted_by: EscrowActorPayload
    reason_code: str = Field(min_length=1, max_length=255)
    reason_detail: str | None = Field(default=None, max_length=4096)
    transition_metadata: dict[str, Any] = Field(default_factory=dict)


class EscrowExecutionUpdateRequest(BaseModel):
    observed_by: EscrowActorPayload
    execution_state: ExecutionState
    provider_execution_ref: str | None = Field(default=None, max_length=255)
    provider_status: str | None = Field(default=None, max_length=255)
    transition_metadata: dict[str, Any] = Field(default_factory=dict)


def to_escrow_record_response(
    record: EscrowRecord,
    *,
    idempotent_replay: bool,
) -> EscrowRecordResponse:
    response = EscrowRecordResponse.model_validate(record, from_attributes=True)
    response.idempotent_replay = idempotent_replay
    return response


def to_capability_release_response(result: EscrowReleaseResult) -> CapabilityReleaseResponse:
    record_response = EscrowRecordResponse.model_validate(result.record, from_attributes=True)
    return CapabilityReleaseResponse(
        **record_response.model_dump(),
        capability_token=result.capability_token,
    )


@router.post("/holds", response_model=EscrowRecordResponse, status_code=status.HTTP_201_CREATED)
def create_escrow_hold(
    payload: EscrowHoldRequest,
    response: Response,
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    issuance_service: Annotated[IssuanceService, Depends(get_issuance_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EscrowRecordResponse:
    try:
        proof = issuance_service.get_proof(payload.issued_proof_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=proof.tenant_id,
            permission=TENANT_ESCROW_WRITE,
        )
        result: EscrowCreateResult = service.create_hold(
            issued_proof_id=payload.issued_proof_id,
            capability_kind=payload.capability_kind,
            protected_resource_ref=payload.protected_resource_ref,
            requested_by=EscrowActor(
                principal_type=payload.requested_by.principal_type,
                principal_id=payload.requested_by.principal_id,
            ),
            expires_in_seconds=payload.expires_in_seconds,
            capability_metadata=payload.capability_metadata,
        )
    except IssuedProofNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (EscrowValidationError, EscrowStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if result.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    return to_escrow_record_response(result.record, idempotent_replay=result.idempotent_replay)


@router.get("", response_model=list[EscrowRecordResponse])
def list_escrow_records(
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    action_intent_record_id: str | None = Query(default=None),
    issued_proof_id: str | None = Query(default=None),
    status_filter: EscrowStatus | None = Query(default=None, alias="status"),
    execution_state_filter: ExecutionState | None = Query(
        default=None,
        alias="execution_state",
    ),
) -> list[EscrowRecordResponse]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_ESCROW_READ,
        )
        records = service.list_records(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            issued_proof_id=issued_proof_id,
            status=status_filter,
            execution_state=execution_state_filter,
        )
        return [to_escrow_record_response(record, idempotent_replay=False) for record in records]
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{escrow_record_id}", response_model=EscrowRecordResponse)
def get_escrow_record(
    escrow_record_id: str,
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EscrowRecordResponse:
    try:
        record = service.get_record(escrow_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_ESCROW_READ,
        )
    except EscrowRecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_escrow_record_response(record, idempotent_replay=False)


@router.post(
    "/{escrow_record_id}/release",
    response_model=CapabilityReleaseResponse,
    status_code=status.HTTP_200_OK,
)
def release_capability(
    escrow_record_id: str,
    payload: EscrowReleaseRequest,
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> CapabilityReleaseResponse:
    try:
        record = service.get_record(escrow_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_ESCROW_WRITE,
        )
        result = service.release_capability(
            escrow_record_id,
            released_by=EscrowActor(
                principal_type=payload.released_by.principal_type,
                principal_id=payload.released_by.principal_id,
            ),
        )
    except EscrowRecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CapabilityReleaseNotAvailableError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except (EscrowValidationError, EscrowStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_capability_release_response(result)


@router.post("/{escrow_record_id}/consume", response_model=EscrowRecordResponse)
def consume_capability(
    escrow_record_id: str,
    payload: EscrowConsumeRequest,
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EscrowRecordResponse:
    try:
        record = service.get_record(escrow_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_ESCROW_WRITE,
        )
        record = service.consume_capability(
            escrow_record_id,
            capability_token=payload.capability_token,
            consumed_by=EscrowActor(
                principal_type=payload.consumed_by.principal_type,
                principal_id=payload.consumed_by.principal_id,
            ),
            provider_execution_ref=payload.provider_execution_ref,
            provider_status=payload.provider_status,
            transition_metadata=payload.transition_metadata,
        )
    except EscrowRecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CapabilityTokenValidationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (EscrowValidationError, EscrowStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_escrow_record_response(record, idempotent_replay=False)


@router.post("/{escrow_record_id}/revoke", response_model=EscrowRecordResponse)
def revoke_capability(
    escrow_record_id: str,
    payload: EscrowInterventionRequest,
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EscrowRecordResponse:
    try:
        record = service.get_record(escrow_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_ESCROW_WRITE,
        )
        record = service.revoke_capability(
            escrow_record_id,
            acted_by=EscrowActor(
                principal_type=payload.acted_by.principal_type,
                principal_id=payload.acted_by.principal_id,
            ),
            reason_code=payload.reason_code,
            reason_detail=payload.reason_detail,
            transition_metadata=payload.transition_metadata,
        )
    except EscrowRecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (EscrowValidationError, EscrowStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_escrow_record_response(record, idempotent_replay=False)


@router.post("/{escrow_record_id}/quarantine", response_model=EscrowRecordResponse)
def quarantine_capability(
    escrow_record_id: str,
    payload: EscrowInterventionRequest,
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EscrowRecordResponse:
    try:
        record = service.get_record(escrow_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_ESCROW_WRITE,
        )
        record = service.quarantine_capability(
            escrow_record_id,
            acted_by=EscrowActor(
                principal_type=payload.acted_by.principal_type,
                principal_id=payload.acted_by.principal_id,
            ),
            reason_code=payload.reason_code,
            reason_detail=payload.reason_detail,
            transition_metadata=payload.transition_metadata,
        )
    except EscrowRecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (EscrowValidationError, EscrowStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_escrow_record_response(record, idempotent_replay=False)


@router.post("/{escrow_record_id}/execution-updates", response_model=EscrowRecordResponse)
def record_execution_update(
    escrow_record_id: str,
    payload: EscrowExecutionUpdateRequest,
    service: Annotated[EscrowService, Depends(get_escrow_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EscrowRecordResponse:
    try:
        record = service.get_record(escrow_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=record.tenant_id,
            permission=TENANT_ESCROW_WRITE,
        )
        record = service.record_execution_update(
            escrow_record_id,
            observed_by=EscrowActor(
                principal_type=payload.observed_by.principal_type,
                principal_id=payload.observed_by.principal_id,
            ),
            execution_state=payload.execution_state,
            provider_execution_ref=payload.provider_execution_ref,
            provider_status=payload.provider_status,
            transition_metadata=payload.transition_metadata,
        )
    except EscrowRecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (EscrowValidationError, EscrowStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_escrow_record_response(record, idempotent_replay=False)
