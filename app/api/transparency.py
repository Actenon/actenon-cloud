from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.api.dependencies import (
    get_auth_service,
    get_current_session,
    get_transparency_log_service,
)
from app.services.auth import (
    PLATFORM_ADMIN_MANAGE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.transparency_format import TransparencyFormatError
from app.services.transparency_log import (
    TransparencyActor,
    TransparencyLogConfigurationError,
    TransparencyLogIntegrityError,
    TransparencyLogNotFoundError,
    TransparencyLogService,
)

router = APIRouter(prefix="/transparency", tags=["transparency"])


class DigestSpecPayload(BaseModel):
    algorithm: str
    canonicalization: str
    value: str = Field(min_length=64, max_length=64)


class DigestIngestRequest(BaseModel):
    receipt_digest: DigestSpecPayload


class DigestIngestResponse(BaseModel):
    log_id: str
    leaf_index: int
    receipt_digest: dict[str, str]
    idempotent_replay: bool


class CheckpointPublishResponse(BaseModel):
    log_id: str
    checkpoint_digest: str
    checkpoint: dict[str, Any]
    idempotent_replay: bool


class InclusionProofResponse(BaseModel):
    proof: dict[str, Any]
    checkpoint: dict[str, Any]


class ConsistencyProofResponse(BaseModel):
    proof: dict[str, Any]
    old_checkpoint: dict[str, Any]
    new_checkpoint: dict[str, Any]


def _require_log_id(service: TransparencyLogService, log_id: str) -> None:
    if log_id != service.log_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"transparency log '{log_id}' was not found",
        )


@router.post(
    "/logs/{log_id}/digests",
    response_model=DigestIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_digest(
    log_id: str,
    payload: DigestIngestRequest,
    response: Response,
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> DigestIngestResponse:
    _require_log_id(service, log_id)
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_ADMIN_MANAGE)
        result = service.append_receipt_digest(payload.receipt_digest.model_dump())
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except TransparencyFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    return DigestIngestResponse(
        log_id=service.log_id,
        leaf_index=result.leaf_index,
        receipt_digest=result.receipt_digest,
        idempotent_replay=result.idempotent_replay,
    )


@router.post(
    "/logs/{log_id}/checkpoints",
    response_model=CheckpointPublishResponse,
    status_code=status.HTTP_201_CREATED,
)
def publish_checkpoint(
    log_id: str,
    response: Response,
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> CheckpointPublishResponse:
    _require_log_id(service, log_id)
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_ADMIN_MANAGE)
        result = service.publish_checkpoint(
            actor=TransparencyActor(
                principal_type=auth_session.principal_type,
                principal_id=auth_session.principal_id,
            )
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except TransparencyLogConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except TransparencyLogNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TransparencyLogIntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if result.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    return CheckpointPublishResponse(
        log_id=service.log_id,
        checkpoint_digest=result.checkpoint_digest,
        checkpoint=result.checkpoint,
        idempotent_replay=result.idempotent_replay,
    )


@router.get("/logs/{log_id}/checkpoints", response_model=list[dict[str, Any]])
def list_checkpoints(
    log_id: str,
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
) -> list[dict[str, Any]]:
    _require_log_id(service, log_id)
    return service.list_checkpoints()


@router.get("/logs/{log_id}/checkpoints/latest", response_model=dict[str, Any])
def latest_checkpoint(
    log_id: str,
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
) -> dict[str, Any]:
    _require_log_id(service, log_id)
    try:
        return service.latest_checkpoint()
    except TransparencyLogNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/logs/{log_id}/proofs/inclusion",
    response_model=InclusionProofResponse,
)
def get_inclusion_proof(
    log_id: str,
    receipt_digest: Annotated[str, Query(min_length=64, max_length=64)],
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
    tree_size: Annotated[int | None, Query(ge=1)] = None,
) -> InclusionProofResponse:
    _require_log_id(service, log_id)
    try:
        proof, checkpoint = service.inclusion_proof(
            receipt_digest,
            tree_size=tree_size,
        )
        return InclusionProofResponse(proof=proof, checkpoint=checkpoint)
    except (TransparencyFormatError, TransparencyLogNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/logs/{log_id}/proofs/consistency",
    response_model=ConsistencyProofResponse,
)
def get_consistency_proof(
    log_id: str,
    old_tree_size: Annotated[int, Query(ge=1)],
    new_tree_size: Annotated[int, Query(ge=1)],
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
) -> ConsistencyProofResponse:
    _require_log_id(service, log_id)
    try:
        proof, old_checkpoint, new_checkpoint = service.consistency_proof(
            old_tree_size=old_tree_size,
            new_tree_size=new_tree_size,
        )
        return ConsistencyProofResponse(
            proof=proof,
            old_checkpoint=old_checkpoint,
            new_checkpoint=new_checkpoint,
        )
    except (TransparencyFormatError, TransparencyLogNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/logs/{log_id}/monitor", response_model=dict[str, Any])
def get_monitor_update(
    log_id: str,
    previous_tree_size: Annotated[int, Query(ge=1)],
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
) -> dict[str, Any]:
    _require_log_id(service, log_id)
    try:
        return service.monitor_update(previous_tree_size=previous_tree_size)
    except (TransparencyFormatError, TransparencyLogNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/logs/{log_id}/integrity", response_model=dict[str, Any])
def get_integrity_report(
    log_id: str,
    service: Annotated[TransparencyLogService, Depends(get_transparency_log_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> dict[str, Any]:
    _require_log_id(service, log_id)
    try:
        auth_service.require_platform_permission(auth_session, PLATFORM_ADMIN_MANAGE)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return service.audit_integrity(record_failure=True).to_dict()
