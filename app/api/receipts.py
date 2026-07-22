from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_auth_service, get_current_session, get_receipt_service
from app.models import ReceiptRecord, ReceiptState
from app.services.auth import (
    TENANT_RECEIPT_READ,
    TENANT_RECEIPT_WRITE,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.receipts import (
    ReceiptActor,
    ReceiptIngestionError,
    ReceiptIngestionResult,
    ReceiptNotFoundError,
    ReceiptService,
)

router = APIRouter(prefix="/receipts", tags=["receipts"])


class ReceiptActorPayload(BaseModel):
    principal_type: Literal["user", "service_principal", "system"]
    principal_id: str = Field(min_length=1, max_length=255)


class ReceiptContractRef(BaseModel):
    contract_family: Literal["receipt"]
    version_ref: str = Field(min_length=1, max_length=255)


class ReceiptIngestRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=32)
    action_intent_record_id: str = Field(min_length=1, max_length=32)
    issued_proof_id: str | None = Field(default=None, max_length=32)
    escrow_record_id: str | None = Field(default=None, max_length=32)
    kernel_contract_ref: ReceiptContractRef
    kernel_receipt: dict[str, Any]
    received_by: ReceiptActorPayload


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    receipt_id: str
    tenant_id: str
    action_intent_record_id: str
    issued_proof_id: str | None
    escrow_record_id: str | None
    contract_family: str
    contract_version_ref: str
    contract_validation_status: str
    contract_validation_errors: list[str]
    external_receipt_id: str
    receipt_type: str
    outcome: str
    receipt_timestamp: datetime
    kernel_receipt_digest: str
    receipt_payload: dict[str, Any]
    receipt_index: dict[str, Any]
    linked_approval_request_ids: list[str]
    linked_approval_decision_ids: list[str]
    linked_evidence_object_ids: list[str]
    provider_execution_ref: str | None
    settlement_reference: str | None
    received_by_principal_type: str
    received_by_principal_id: str
    receipt_state: ReceiptState
    reconciliation_summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    idempotent_replay: bool = False


def to_receipt_response(
    receipt: ReceiptRecord,
    *,
    idempotent_replay: bool,
) -> ReceiptResponse:
    response = ReceiptResponse.model_validate(receipt, from_attributes=True)
    response.idempotent_replay = idempotent_replay
    return response


@router.post("", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
def ingest_receipt(
    payload: ReceiptIngestRequest,
    response: Response,
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ReceiptResponse:
    try:
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=payload.tenant_id,
            permission=TENANT_RECEIPT_WRITE,
        )
        result: ReceiptIngestionResult = service.ingest_receipt(
            tenant_id=payload.tenant_id,
            action_intent_record_id=payload.action_intent_record_id,
            contract_family=payload.kernel_contract_ref.contract_family,
            contract_version_ref=payload.kernel_contract_ref.version_ref,
            kernel_receipt=payload.kernel_receipt,
            received_by=ReceiptActor(
                principal_type=payload.received_by.principal_type,
                principal_id=payload.received_by.principal_id,
            ),
            issued_proof_id=payload.issued_proof_id,
            escrow_record_id=payload.escrow_record_id,
        )
    except ReceiptIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if result.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    return to_receipt_response(result.receipt, idempotent_replay=result.idempotent_replay)


@router.get("", response_model=list[ReceiptResponse])
def list_receipts(
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    action_intent_record_id: str | None = Query(default=None),
    issued_proof_id: str | None = Query(default=None),
    escrow_record_id: str | None = Query(default=None),
    receipt_type: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    provider_execution_ref: str | None = Query(default=None),
) -> list[ReceiptResponse]:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_RECEIPT_READ,
        )
        receipts = service.list_receipts(
            tenant_id=tenant_id,
            action_intent_record_id=action_intent_record_id,
            issued_proof_id=issued_proof_id,
            escrow_record_id=escrow_record_id,
            receipt_type=receipt_type,
            outcome=outcome,
            currency=currency,
            provider_execution_ref=provider_execution_ref,
        )
        return [to_receipt_response(receipt, idempotent_replay=False) for receipt in receipts]
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(
    receipt_id: str,
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> ReceiptResponse:
    try:
        receipt = service.get_receipt(receipt_id)
        auth_service.require_tenant_permission(
            auth_session,
            tenant_id=receipt.tenant_id,
            permission=TENANT_RECEIPT_READ,
        )
    except ReceiptNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return to_receipt_response(receipt, idempotent_replay=False)
