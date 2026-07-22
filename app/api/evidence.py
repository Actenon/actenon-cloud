from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_auth_service, get_current_session, get_evidence_service
from app.models import EvidenceObject, EvidenceStatus, EvidenceStorageMode, EvidenceType
from app.services.auth import (
    TENANT_EVIDENCE_READ,
    TENANT_EVIDENCE_WRITE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.evidence import (
    EvidenceBackendUnavailableError,
    EvidenceContentUnavailableError,
    EvidenceObjectNotFoundError,
    EvidencePrincipal,
    EvidenceService,
    EvidenceValidationError,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])


class EvidenceRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tenant_id: str = Field(min_length=1, max_length=32)
    action_intent_record_id: str = Field(min_length=1, max_length=32)
    approval_request_id: str | None = Field(default=None, max_length=32)
    evidence_type: EvidenceType
    storage_mode: EvidenceStorageMode
    storage_ref: str = Field(min_length=1, max_length=1_024)
    original_filename: str | None = Field(default=None, max_length=255)
    media_type: str | None = Field(default=None, max_length=255)
    content_digest: str | None = Field(default=None, min_length=1, max_length=64)
    size_bytes: int | None = Field(default=None, ge=0)
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_object_id: str
    tenant_id: str
    action_intent_record_id: str
    approval_request_id: str | None
    evidence_type: EvidenceType
    storage_mode: EvidenceStorageMode
    storage_ref: str
    original_filename: str | None
    media_type: str | None
    content_digest: str | None
    size_bytes: int | None
    uploaded_by_principal_type: str
    uploaded_by_principal_id: str
    evidence_metadata: dict[str, Any]
    expires_at: datetime | None
    status: EvidenceStatus
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[EvidenceResponse])
def list_evidence(
    service: Annotated[EvidenceService, Depends(get_evidence_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    action_intent_record_id: str | None = Query(default=None),
    approval_request_id: str | None = Query(default=None),
) -> list[EvidenceObject]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_EVIDENCE_READ,
        )
        return service.list_evidence(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            approval_request_id=approval_request_id,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{evidence_object_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_object_id: str,
    service: Annotated[EvidenceService, Depends(get_evidence_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EvidenceObject:
    try:
        evidence = service.get_evidence(evidence_object_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=evidence.tenant_id,
            permission=TENANT_EVIDENCE_READ,
        )
        return evidence
    except EvidenceObjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{evidence_object_id}/content")
def get_evidence_content(
    evidence_object_id: str,
    service: Annotated[EvidenceService, Depends(get_evidence_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    disposition: Literal["inline", "attachment"] = Query(default="attachment"),
) -> FileResponse:
    try:
        evidence_content = service.get_evidence_content(evidence_object_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=evidence_content.evidence_object.tenant_id,
            permission=TENANT_EVIDENCE_READ,
        )
    except EvidenceObjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EvidenceContentUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    evidence_object = evidence_content.evidence_object
    filename = evidence_object.original_filename or f"{evidence_object.evidence_object_id}.bin"
    return FileResponse(
        evidence_content.path,
        filename=filename,
        media_type=evidence_object.media_type or "application/octet-stream",
        content_disposition_type=disposition,
    )


@router.post("/register", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def register_evidence(
    payload: EvidenceRegisterRequest,
    service: Annotated[EvidenceService, Depends(get_evidence_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> EvidenceObject:
    try:
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=payload.tenant_id,
            permission=TENANT_EVIDENCE_WRITE,
        )
        return service.register_evidence(
            tenant_id=payload.tenant_id,
            action_intent_record_id=payload.action_intent_record_id,
            approval_request_id=payload.approval_request_id,
            evidence_type=payload.evidence_type,
            storage_mode=payload.storage_mode,
            storage_ref=payload.storage_ref,
            original_filename=payload.original_filename,
            media_type=payload.media_type,
            content_digest=payload.content_digest,
            size_bytes=payload.size_bytes,
            uploaded_by=EvidencePrincipal(
                principal_type=auth_session.principal_type,
                principal_id=auth_session.principal_id,
            ),
            evidence_metadata=payload.evidence_metadata,
            expires_at=payload.expires_at,
        )
    except EvidenceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EvidenceBackendUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/upload", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    service: Annotated[EvidenceService, Depends(get_evidence_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: Annotated[str, Form(min_length=1, max_length=32)],
    action_intent_record_id: Annotated[str, Form(min_length=1, max_length=32)],
    approval_request_id: Annotated[str | None, Form(max_length=32)] = None,
    evidence_type: Annotated[EvidenceType, Form()] = EvidenceType.document,
    expires_at: Annotated[str | None, Form()] = None,
    evidence_metadata_json: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
) -> EvidenceObject:
    try:
        metadata = json.loads(evidence_metadata_json) if evidence_metadata_json else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="evidence_metadata_json must be valid JSON",
        ) from exc

    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="evidence_metadata_json must decode to a JSON object",
        )

    parsed_expires_at: datetime | None = None
    if expires_at:
        try:
            parsed_expires_at = datetime.fromisoformat(expires_at)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expires_at must be a valid ISO-8601 datetime",
            ) from exc

    try:
        payload = await file.read()
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_EVIDENCE_WRITE,
        )
        return service.upload_evidence(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            approval_request_id=approval_request_id,
            evidence_type=evidence_type,
            uploaded_by=EvidencePrincipal(
                principal_type=auth_session.principal_type,
                principal_id=auth_session.principal_id,
            ),
            original_filename=file.filename or "upload.bin",
            media_type=file.content_type,
            evidence_metadata=metadata,
            expires_at=parsed_expires_at,
            payload=payload,
        )
    except EvidenceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
