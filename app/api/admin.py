from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_auth_service, get_current_session
from app.models import MembershipStatus, Role, RoleScope, ServicePrincipal, TenantMembership, User
from app.services.auth import (
    PLATFORM_AUTH_MANAGE,
    TENANT_MEMBERSHIP_MANAGE,
    AuthConflictError,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
    AuthValidationError,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=255)
    platform_role_ids: list[str] = Field(default_factory=list)
    identity_provider_subject: str | None = Field(default=None, max_length=255)
    auth_metadata: dict[str, Any] = Field(default_factory=dict)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    display_name: str
    identity_provider_subject: str | None
    platform_role_ids: list[str]
    auth_metadata: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scope: RoleScope
    tenant_id: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=2048)
    permissions: list[str] = Field(min_length=1)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: str
    role_key: str
    tenant_id: str | None
    scope: RoleScope
    name: str
    description: str | None
    permissions: list[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime


class MembershipCreateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=32)
    role_ids: list[str] = Field(min_length=1)


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    membership_id: str
    tenant_id: str
    user_id: str
    role_ids: list[str]
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime


class ServicePrincipalCreateRequest(BaseModel):
    tenant_id: str | None = Field(default=None, max_length=32)
    display_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2048)
    role_ids: list[str] = Field(default_factory=list)
    auth_metadata: dict[str, Any] = Field(default_factory=dict)


class ServicePrincipalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_principal_id: str
    tenant_id: str | None
    display_name: str
    description: str | None
    role_ids: list[str]
    auth_mode: str
    status: str
    auth_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> User:
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_AUTH_MANAGE)
        return auth_service.create_user(
            email=payload.email,
            display_name=payload.display_name,
            platform_role_ids=payload.platform_role_ids,
            identity_provider_subject=payload.identity_provider_subject,
            auth_metadata=payload.auth_metadata,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/users", response_model=list[UserResponse])
def list_users(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[User]:
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_AUTH_MANAGE)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return auth_service.list_users()


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> Role:
    try:
        if payload.scope == RoleScope.platform:
            auth_service.require_platform_permission(auth_session, PLATFORM_AUTH_MANAGE)
        else:
            if payload.tenant_id is None:
                raise AuthValidationError("tenant_id is required for tenant-scoped roles")
            auth_service.require_tenant_permission(
                auth_session,
                tenant_id=payload.tenant_id,
                permission=TENANT_MEMBERSHIP_MANAGE,
            )
        return auth_service.create_role(
            name=payload.name,
            scope=payload.scope,
            permissions=payload.permissions,
            description=payload.description,
            tenant_id=payload.tenant_id,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    scope: RoleScope | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
) -> list[Role]:
    try:
        if auth_session.is_platform_admin:
            return auth_service.list_roles(scope=scope, tenant_id=tenant_id)
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_MEMBERSHIP_MANAGE,
        )
        return auth_service.list_roles(scope=scope, tenant_id=tenant_id)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/tenants/{tenant_id}/memberships",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_membership(
    tenant_id: str,
    payload: MembershipCreateRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> TenantMembership:
    try:
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_MEMBERSHIP_MANAGE,
        )
        return auth_service.create_membership(
            tenant_id=tenant_id,
            user_id=payload.user_id,
            role_ids=payload.role_ids,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/tenants/{tenant_id}/memberships", response_model=list[MembershipResponse])
def list_memberships(
    tenant_id: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[TenantMembership]:
    try:
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_MEMBERSHIP_MANAGE,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return auth_service.list_memberships(tenant_id)


@router.post(
    "/service-principals",
    response_model=ServicePrincipalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service_principal(
    payload: ServicePrincipalCreateRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ServicePrincipal:
    try:
        if payload.tenant_id is None:
            auth_service.require_platform_permission(auth_session, PLATFORM_AUTH_MANAGE)
        else:
            auth_service.require_tenant_permission(
                auth_session,
                tenant_id=payload.tenant_id,
                permission=TENANT_MEMBERSHIP_MANAGE,
            )
        return auth_service.create_service_principal(
            tenant_id=payload.tenant_id,
            display_name=payload.display_name,
            description=payload.description,
            role_ids=payload.role_ids,
            auth_metadata=payload.auth_metadata,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/service-principals", response_model=list[ServicePrincipalResponse])
def list_service_principals(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
) -> list[ServicePrincipal]:
    try:
        if tenant_id is None:
            auth_service.require_platform_permission(auth_session, PLATFORM_AUTH_MANAGE)
            return auth_service.list_service_principals()
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_MEMBERSHIP_MANAGE,
        )
        return auth_service.list_service_principals(tenant_id=tenant_id)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
