from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_auth_service, get_current_session
from app.services.auth import (
    PLATFORM_AUTH_MANAGE,
    AuthConflictError,
    AuthenticatedSession,
    AuthenticationError,
    AuthorizationError,
    AuthService,
    AuthValidationError,
    IssuedToken,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class BootstrapPlatformAdminRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=255)


class TokenIssueRequest(BaseModel):
    expires_in_seconds: int | None = Field(default=None, ge=300, le=604800)


class OperatorTokenIssueRequest(TokenIssueRequest):
    user_id: str = Field(min_length=1, max_length=32)


class ServiceTokenIssueRequest(TokenIssueRequest):
    service_principal_id: str = Field(min_length=1, max_length=32)


class TenantAccessResponse(BaseModel):
    tenant_id: str
    role_names: list[str]
    permissions: list[str]


class SessionResponse(BaseModel):
    principal_type: str
    principal_id: str
    display_name: str
    token_kind: str
    auth_mode: str
    issued_at: datetime
    expires_at: datetime
    platform_roles: list[str]
    platform_permissions: list[str]
    tenant_access: list[TenantAccessResponse]


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    session: SessionResponse


def to_session_response(auth_session: AuthenticatedSession) -> SessionResponse:
    tenant_access = [
        TenantAccessResponse(
            tenant_id=tenant_id,
            role_names=list(auth_session.tenant_roles.get(tenant_id, ())),
            permissions=sorted(auth_session.tenant_permissions.get(tenant_id, frozenset())),
        )
        for tenant_id in sorted(auth_session.tenant_permissions)
    ]
    return SessionResponse(
        principal_type=auth_session.principal_type,
        principal_id=auth_session.principal_id,
        display_name=auth_session.display_name,
        token_kind=auth_session.token_kind,
        auth_mode=auth_session.auth_mode,
        issued_at=auth_session.issued_at,
        expires_at=auth_session.expires_at,
        platform_roles=list(auth_session.platform_roles),
        platform_permissions=sorted(auth_session.platform_permissions),
        tenant_access=tenant_access,
    )


def to_access_token_response(
    token: IssuedToken,
    auth_session: AuthenticatedSession,
) -> AccessTokenResponse:
    return AccessTokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_at=token.expires_at,
        session=to_session_response(auth_session),
    )


@router.post(
    "/bootstrap/platform-admin",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_platform_admin(
    payload: BootstrapPlatformAdminRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    bootstrap_token: Annotated[
        str | None,
        Header(alias="X-Action-Control-Plane-Bootstrap-Token"),
    ] = None,
) -> AccessTokenResponse:
    try:
        _, token = auth_service.bootstrap_platform_admin(
            bootstrap_token=bootstrap_token or "",
            email=payload.email,
            display_name=payload.display_name,
        )
        auth_session = auth_service.authenticate_bearer_token(token.access_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (AuthValidationError, AuthConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return to_access_token_response(token, auth_session)


@router.get("/session", response_model=SessionResponse)
def get_auth_session(
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> SessionResponse:
    return to_session_response(auth_session)


@router.post("/dev/operator-token", response_model=AccessTokenResponse)
def issue_operator_token(
    payload: OperatorTokenIssueRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> AccessTokenResponse:
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_AUTH_MANAGE)
        token = auth_service.issue_operator_token(
            payload.user_id,
            expires_in_seconds=payload.expires_in_seconds,
        )
        token_session = auth_service.authenticate_bearer_token(token.access_token)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_access_token_response(token, token_session)


@router.post("/dev/service-token", response_model=AccessTokenResponse)
def issue_service_token(
    payload: ServiceTokenIssueRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> AccessTokenResponse:
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_AUTH_MANAGE)
        token = auth_service.issue_service_token(
            payload.service_principal_id,
            expires_in_seconds=payload.expires_in_seconds,
        )
        token_session = auth_service.authenticate_bearer_token(token.access_token)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_access_token_response(token, token_session)
