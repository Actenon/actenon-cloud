from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_auth_service, get_current_session, get_db_session
from app.models import FinanceProfile, Tenant
from app.services.auth import (
    PLATFORM_TENANTS_MANAGE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.policy_engine import PolicyManagementService, TenantNotFoundError

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    finance_profile: FinanceProfile


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: str
    display_name: str
    status: str
    finance_profile: str
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreateRequest,
    session: Annotated[Session, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> Tenant:
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_TENANTS_MANAGE)
        return PolicyManagementService(session).create_tenant(
            display_name=payload.display_name,
            finance_profile=payload.finance_profile.value,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("", response_model=list[TenantResponse])
def list_tenants(
    session: Annotated[Session, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[Tenant]:
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_TENANTS_MANAGE)
        return PolicyManagementService(session).list_tenants()
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> Tenant:
    try:
        tenant = PolicyManagementService(session).get_tenant(tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        if not auth_session.is_platform_admin:
            auth_service.require_tenant_access(auth_session, tenant_id)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return tenant
