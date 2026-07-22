from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import (
    get_auth_service,
    get_current_session,
    get_issuer_registry_service,
)
from app.models import IssuerRegistryAuditEvent, IssuerRegistryRecord, IssuerStanding
from app.services.auth import (
    PLATFORM_ADMIN_MANAGE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.issuer_registry import (
    ISSUER_REGISTRY_ADMIN_PERMISSIONS,
    IssuerRegistryActor,
    IssuerRegistryAuthorizationError,
    IssuerRegistryConfigurationError,
    IssuerRegistryConflictError,
    IssuerRegistryNotFoundError,
    IssuerRegistryService,
    IssuerRegistryStateError,
)
from app.services.issuer_status_format import IssuerStatusFormatError

router = APIRouter(prefix="/issuer-registry", tags=["issuer-registry"])


class IssuerRegistrationRequest(BaseModel):
    issuer_type: str = Field(min_length=1, max_length=64)
    issuer_id: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, min_length=1, max_length=256)
    registry_metadata: dict[str, Any] = Field(default_factory=dict)


class StandingChangeRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4096)


class IssuerRegistryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    registry_id: str
    issuer_type: str
    issuer_id: str
    display_name: str | None
    standing: IssuerStanding
    standing_reason: str | None
    status_version: int
    registry_metadata: dict[str, Any]
    registered_at: datetime
    standing_changed_at: datetime
    revoked_at: datetime | None


class StatusPublicationResponse(BaseModel):
    registry_id: str
    status_version: int
    artifact: dict[str, Any]


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    actor_principal_type: str
    actor_principal_id: str
    reason: str | None
    prior_state: dict[str, Any] | None
    resulting_state: dict[str, Any] | None
    details: dict[str, Any]
    created_at: datetime


def _admin_actor(
    auth_service: AuthService,
    auth_session: AuthenticatedSession,
) -> IssuerRegistryActor:
    auth_service.require_platform_permission(auth_session, PLATFORM_ADMIN_MANAGE)
    return IssuerRegistryActor(
        principal_type=auth_session.principal_type,
        principal_id=auth_session.principal_id,
        permissions=ISSUER_REGISTRY_ADMIN_PERMISSIONS,
    )


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, (AuthorizationError, IssuerRegistryAuthorizationError)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    if isinstance(exc, IssuerRegistryNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, IssuerRegistryConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if isinstance(exc, (IssuerRegistryStateError, IssuerStatusFormatError)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if isinstance(exc, IssuerRegistryConfigurationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    raise exc


@router.post(
    "/issuers",
    response_model=IssuerRegistryResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_issuer(
    payload: IssuerRegistrationRequest,
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IssuerRegistryRecord:
    try:
        actor = _admin_actor(auth_service, auth_session)
        identity: dict[str, str] = {
            "type": payload.issuer_type,
            "id": payload.issuer_id,
        }
        if payload.display_name is not None:
            identity["display_name"] = payload.display_name
        return service.register_issuer(
            identity,
            actor=actor,
            registry_metadata=payload.registry_metadata,
        )
    except Exception as exc:
        _raise_service_error(exc)
        raise


@router.get("/issuers", response_model=list[IssuerRegistryResponse])
def list_issuers(
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[IssuerRegistryRecord]:
    try:
        _admin_actor(auth_service, auth_session)
        return service.list_issuers()
    except Exception as exc:
        _raise_service_error(exc)
        raise


@router.get("/issuers/{registry_id}", response_model=IssuerRegistryResponse)
def get_issuer(
    registry_id: str,
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IssuerRegistryRecord:
    try:
        _admin_actor(auth_service, auth_session)
        return service.get_issuer(registry_id)
    except Exception as exc:
        _raise_service_error(exc)
        raise


def _change_standing(
    registry_id: str,
    payload: StandingChangeRequest,
    *,
    operation: str,
    service: IssuerRegistryService,
    auth_service: AuthService,
    auth_session: AuthenticatedSession,
) -> IssuerRegistryRecord | StatusPublicationResponse:
    actor = _admin_actor(auth_service, auth_session)
    if operation == "suspend":
        return service.suspend_issuer(
            registry_id,
            reason=payload.reason,
            actor=actor,
        )
    if operation == "reinstate":
        return service.reinstate_issuer(
            registry_id,
            reason=payload.reason,
            actor=actor,
        )
    revoked = service.revoke_issuer(
        registry_id,
        reason=payload.reason,
        actor=actor,
    )
    return StatusPublicationResponse(
        registry_id=revoked.issuer.registry_id,
        status_version=revoked.publication.publication.status_version,
        artifact=revoked.publication.artifact,
    )


@router.post(
    "/issuers/{registry_id}/suspend",
    response_model=IssuerRegistryResponse,
)
def suspend_issuer(
    registry_id: str,
    payload: StandingChangeRequest,
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IssuerRegistryRecord:
    try:
        result = _change_standing(
            registry_id,
            payload,
            operation="suspend",
            service=service,
            auth_service=auth_service,
            auth_session=auth_session,
        )
        return cast(IssuerRegistryRecord, result)
    except Exception as exc:
        _raise_service_error(exc)
        raise


@router.post(
    "/issuers/{registry_id}/reinstate",
    response_model=IssuerRegistryResponse,
)
def reinstate_issuer(
    registry_id: str,
    payload: StandingChangeRequest,
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IssuerRegistryRecord:
    try:
        result = _change_standing(
            registry_id,
            payload,
            operation="reinstate",
            service=service,
            auth_service=auth_service,
            auth_session=auth_session,
        )
        return cast(IssuerRegistryRecord, result)
    except Exception as exc:
        _raise_service_error(exc)
        raise


@router.post(
    "/issuers/{registry_id}/revoke",
    response_model=StatusPublicationResponse,
)
def revoke_issuer(
    registry_id: str,
    payload: StandingChangeRequest,
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> StatusPublicationResponse:
    try:
        result = _change_standing(
            registry_id,
            payload,
            operation="revoke",
            service=service,
            auth_service=auth_service,
            auth_session=auth_session,
        )
        return cast(StatusPublicationResponse, result)
    except Exception as exc:
        _raise_service_error(exc)
        raise


@router.post(
    "/issuers/{registry_id}/status",
    response_model=StatusPublicationResponse,
)
def publish_status(
    registry_id: str,
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> StatusPublicationResponse:
    try:
        actor = _admin_actor(auth_service, auth_session)
        result = service.publish_status(registry_id, actor=actor)
        return StatusPublicationResponse(
            registry_id=registry_id,
            status_version=result.publication.status_version,
            artifact=result.artifact,
        )
    except Exception as exc:
        _raise_service_error(exc)
        raise


@router.get(
    "/issuers/{registry_id}/audit",
    response_model=list[AuditEventResponse],
)
def list_audit_events(
    registry_id: str,
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[IssuerRegistryAuditEvent]:
    try:
        _admin_actor(auth_service, auth_session)
        return service.list_audit_events(registry_id)
    except Exception as exc:
        _raise_service_error(exc)
        raise


@router.get("/status", response_model=dict[str, Any])
def get_current_status(
    issuer_type: Annotated[str, Query(min_length=1, max_length=64)],
    issuer_id: Annotated[str, Query(min_length=1, max_length=512)],
    service: Annotated[IssuerRegistryService, Depends(get_issuer_registry_service)],
) -> dict[str, Any]:
    """Public verifier endpoint. It never serves a prior registry-state version."""

    try:
        return service.latest_status_artifact(
            issuer_type=issuer_type,
            issuer_id=issuer_id,
        )
    except Exception as exc:
        _raise_service_error(exc)
        raise


__all__ = ["router"]
