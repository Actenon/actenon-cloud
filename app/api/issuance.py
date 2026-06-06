from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import (
    get_action_intent_service,
    get_auth_service,
    get_current_session,
    get_issuance_service,
    get_signing_service,
)
from app.models import (
    IssuedProof,
    ProofIssuanceStatus,
    ProofKind,
    SigningAlgorithm,
    SigningKeyBackend,
    SigningKeyPurpose,
    SigningKeyReference,
    SigningKeyStatus,
    SigningOperationStatus,
    TrustTier,
)
from app.services.action_intents import ActionIntentNotFoundError, ActionIntentService
from app.services.auth import (
    TENANT_ISSUANCE_READ,
    TENANT_ISSUANCE_WRITE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.issuance import (
    IssuanceService,
    IssuedProofNotFoundError,
    IssuerActor,
    ProofIssuanceError,
)
from app.services.signing import (
    SigningConfigurationError,
    SigningKeyNotFoundError,
    SigningKeyStateError,
    SigningService,
)

router = APIRouter(prefix="/issuance", tags=["issuance"])


class IssuanceRequestedBy(BaseModel):
    principal_type: Literal["user", "service_principal", "system"]
    principal_id: str = Field(min_length=1, max_length=255)


class SigningKeyCreateRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=255)
    key_purpose: SigningKeyPurpose = SigningKeyPurpose.pccb_signing
    algorithm: SigningAlgorithm = SigningAlgorithm.hs256
    key_backend: SigningKeyBackend = SigningKeyBackend.development_local_hmac
    provider_key_ref: str | None = Field(default=None, max_length=255)
    public_key_ref: str | None = Field(default=None, max_length=1024)
    issuer_name: str | None = Field(default=None, max_length=255)
    issuer_uri: str | None = Field(default=None, max_length=1024)
    trust_tier: TrustTier | None = None
    lifecycle_metadata: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = True


class SigningKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signing_key_reference_id: str
    tenant_id: str
    display_name: str
    issuer_name: str
    issuer_uri: str
    trust_tier: TrustTier
    key_purpose: SigningKeyPurpose
    algorithm: SigningAlgorithm
    key_backend: SigningKeyBackend
    provider_key_ref: str
    public_key_ref: str | None
    status: SigningKeyStatus
    is_default: bool
    lifecycle_metadata: dict[str, Any]
    activated_at: datetime | None
    suspended_at: datetime | None
    revoked_at: datetime | None
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SigningOperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signing_operation_id: str
    signing_key_reference_id: str
    algorithm: SigningAlgorithm
    key_backend: SigningKeyBackend
    status: SigningOperationStatus
    payload_digest: str
    signature: str | None
    provider_operation_ref: str | None
    error_detail: str | None
    requested_at: datetime
    completed_at: datetime | None


class ProofIssueRequest(BaseModel):
    action_intent_record_id: str = Field(min_length=1, max_length=32)
    proof_kind: ProofKind = ProofKind.pccb
    audience: str = Field(min_length=1, max_length=255)
    scope: list[str] = Field(min_length=1)
    expires_in_seconds: int | None = Field(default=None, ge=60, le=2_592_000)
    requested_by: IssuanceRequestedBy
    signing_key_reference_id: str | None = Field(default=None, max_length=32)


class IssuedProofResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issued_proof_id: str
    tenant_id: str
    action_intent_record_id: str
    signing_key_reference_id: str | None
    proof_kind: ProofKind
    status: ProofIssuanceStatus
    issuer_name: str
    issuer_uri: str
    trust_tier: TrustTier
    audience: str
    scope: list[str]
    scope_hash: str
    nonce: str
    action_intent_digest: str
    proof_payload: dict[str, Any]
    proof_payload_digest: str
    signature: str | None
    algorithm: SigningAlgorithm | None
    issued_by_principal_type: str
    issued_by_principal_id: str
    issuance_trace: list[dict[str, Any]]
    failure_reason: str | None
    revocation_reason_code: str | None
    revocation_reason_detail: str | None
    revocation_reference: str | None
    issued_at: datetime | None
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    signing_operations: list[SigningOperationResponse]
    idempotent_replay: bool = False


def to_issued_proof_response(
    proof: IssuedProof,
    *,
    idempotent_replay: bool,
) -> IssuedProofResponse:
    response = IssuedProofResponse.model_validate(proof, from_attributes=True)
    response.idempotent_replay = idempotent_replay
    return response


@router.post("/keys", response_model=SigningKeyResponse, status_code=status.HTTP_201_CREATED)
def create_signing_key(
    payload: SigningKeyCreateRequest,
    service: Annotated[SigningService, Depends(get_signing_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> SigningKeyReference:
    try:
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=payload.tenant_id,
            permission=TENANT_ISSUANCE_WRITE,
        )
        return service.register_key(
            tenant_id=payload.tenant_id,
            display_name=payload.display_name,
            key_purpose=payload.key_purpose,
            algorithm=payload.algorithm,
            key_backend=payload.key_backend,
            provider_key_ref=payload.provider_key_ref,
            public_key_ref=payload.public_key_ref,
            issuer_name=payload.issuer_name,
            issuer_uri=payload.issuer_uri,
            trust_tier=payload.trust_tier,
            lifecycle_metadata=payload.lifecycle_metadata,
            is_default=payload.is_default,
        )
    except (SigningKeyStateError, SigningConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/keys", response_model=list[SigningKeyResponse])
def list_signing_keys(
    service: Annotated[SigningService, Depends(get_signing_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    key_purpose: SigningKeyPurpose | None = Query(default=None),
    status_filter: SigningKeyStatus | None = Query(default=None, alias="status"),
) -> list[SigningKeyReference]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_ISSUANCE_READ,
        )
        return service.list_keys(
            tenant_id=tenant_id,
            key_purpose=key_purpose,
            status=status_filter,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/keys/{signing_key_reference_id}", response_model=SigningKeyResponse)
def get_signing_key(
    signing_key_reference_id: str,
    service: Annotated[SigningService, Depends(get_signing_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> SigningKeyReference:
    try:
        key = service.get_key(signing_key_reference_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=key.tenant_id,
            permission=TENANT_ISSUANCE_READ,
        )
        return key
    except SigningKeyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/keys/{signing_key_reference_id}/activate", response_model=SigningKeyResponse)
def activate_signing_key(
    signing_key_reference_id: str,
    service: Annotated[SigningService, Depends(get_signing_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> SigningKeyReference:
    try:
        key = service.get_key(signing_key_reference_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=key.tenant_id,
            permission=TENANT_ISSUANCE_WRITE,
        )
        return service.activate_key(signing_key_reference_id)
    except SigningKeyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SigningKeyStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/keys/{signing_key_reference_id}/suspend", response_model=SigningKeyResponse)
def suspend_signing_key(
    signing_key_reference_id: str,
    service: Annotated[SigningService, Depends(get_signing_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> SigningKeyReference:
    try:
        key = service.get_key(signing_key_reference_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=key.tenant_id,
            permission=TENANT_ISSUANCE_WRITE,
        )
        return service.suspend_key(signing_key_reference_id)
    except SigningKeyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SigningKeyStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/proofs", response_model=IssuedProofResponse, status_code=status.HTTP_201_CREATED)
def issue_proof(
    payload: ProofIssueRequest,
    response: Response,
    service: Annotated[IssuanceService, Depends(get_issuance_service)],
    action_intent_service: Annotated[ActionIntentService, Depends(get_action_intent_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IssuedProofResponse:
    try:
        action_intent = action_intent_service.get_record(payload.action_intent_record_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=action_intent.tenant_id,
            permission=TENANT_ISSUANCE_WRITE,
        )
        result = service.issue_proof(
            action_intent_record_id=payload.action_intent_record_id,
            proof_kind=payload.proof_kind,
            audience=payload.audience,
            scope=payload.scope,
            expires_in_seconds=payload.expires_in_seconds,
            requested_by=IssuerActor(
                principal_type=payload.requested_by.principal_type,
                principal_id=payload.requested_by.principal_id,
            ),
            signing_key_reference_id=payload.signing_key_reference_id,
        )
    except ProofIssuanceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ActionIntentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if result.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    return to_issued_proof_response(result.proof, idempotent_replay=result.idempotent_replay)


@router.get("/proofs", response_model=list[IssuedProofResponse])
def list_issued_proofs(
    service: Annotated[IssuanceService, Depends(get_issuance_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    action_intent_record_id: str | None = Query(default=None),
    status_filter: ProofIssuanceStatus | None = Query(default=None, alias="status"),
) -> list[IssuedProofResponse]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_ISSUANCE_READ,
        )
        proofs = service.list_proofs(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            status=status_filter,
        )
        return [
            to_issued_proof_response(proof, idempotent_replay=False)
            for proof in proofs
        ]
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/proofs/{issued_proof_id}", response_model=IssuedProofResponse)
def get_issued_proof(
    issued_proof_id: str,
    service: Annotated[IssuanceService, Depends(get_issuance_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IssuedProofResponse:
    try:
        proof = service.get_proof(issued_proof_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=proof.tenant_id,
            permission=TENANT_ISSUANCE_READ,
        )
    except IssuedProofNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_issued_proof_response(proof, idempotent_replay=False)
