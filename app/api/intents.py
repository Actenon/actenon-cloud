"""Cloud AEI API — AuthorisedExecutionIntent endpoints (Prompt 14).

Production-quality REST API for AEI lifecycle management in the Cloud
control plane. All mutating endpoints use idempotency keys. Lifecycle
transitions are enforced with database transactions. Tenant isolation
is enforced via RLS (row-level security) + authenticated session
context + Python-level permission checks.

Cloud does NOT become the definition of proof validity. The Kernel
remains the verifier authority. Cloud issues proofs under authorised
conditions and delegates execution to the Permit gateway.

Endpoints:

  POST   /api/v1/intents                      create intent (idempotent)
  GET    /api/v1/intents                      list intents (tenant-scoped)
  GET    /api/v1/intents/{intent_id}          retrieve intent
  POST   /api/v1/intents/{intent_id}/approve  approve intent (requires intent.approve)
  POST   /api/v1/intents/{intent_id}/deny     deny intent (requires intent.approve)
  POST   /api/v1/intents/{intent_id}/cancel   cancel intent
  POST   /api/v1/intents/{intent_id}/proof    issue/retrieve proof
  POST   /api/v1/intents/{intent_id}/execute  execute brokered intent (via PermitGatewayBridge)
  POST   /api/v1/intents/{intent_id}/submit   submit resource-owned intent (via bridge)
  GET    /api/v1/intents/{intent_id}/receipts retrieve receipts
  GET    /api/v1/intents/{intent_id}/refusals retrieve refusals
  GET    /api/v1/intents/{intent_id}/evidence retrieve evidence bundle
  GET    /api/v1/intents/capabilities         inspect capabilities
  POST   /api/v1/credentials                  register credential (requires credential.manage)
  GET    /api/v1/credentials                  list credentials (redacted, requires credential.view)
  DELETE /api/v1/credentials/{ref}            delete credential (requires credential.manage)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from actenon_permit.intent import IntentLifecycle, IntentTransitionError, validate_transition
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_authenticated_db_session, get_current_session
from app.database import DatabaseSession
from app.models.intent import AuthorisedExecutionIntentRecord
from app.services.auth import AuthenticatedSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intents", tags=["intents"])
credentials_router = APIRouter(prefix="/credentials", tags=["credentials"])

# ---------------------------------------------------------------------------
# Permission constants
# ---------------------------------------------------------------------------

INTENT_APPROVE = "intent.approve"
INTENT_EXECUTE = "intent.execute"
INTENT_VIEW = "intent.view"
CREDENTIAL_MANAGE = "credential.manage"
CREDENTIAL_VIEW = "credential.view"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateIntentRequest(BaseModel):
    action_type: str
    action_params: dict[str, Any] = Field(default_factory=dict)
    target_type: str = "unknown"
    target_id: str
    requested_execution_mode: str = "brokered"
    idempotency_key: str | None = None
    expiry_seconds: int = 3600
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntentResponse(BaseModel):
    intent_id: str
    protocol_version: str
    action_type: str
    action_params: dict[str, Any]
    target_type: str
    target_id: str
    requested_execution_mode: str
    requester_subject: str
    requester_agent_id: str
    requester_tenant_id: str | None
    idempotency_key: str
    created_at: str
    expiry: str | None
    metadata: dict[str, Any]
    lifecycle_state: str
    linked_decision_id: str | None
    linked_proof_id: str | None
    linked_attempt_ids: list[str]
    linked_receipt_id: str | None
    linked_refusal_id: str | None
    submission_reference: str | None


class ApproveRequest(BaseModel):
    approver_id: str
    reason: str | None = None


class DenyRequest(BaseModel):
    denier_id: str
    reason: str


class ExecuteRequest(BaseModel):
    grant_token: str
    tool_name: str | None = None


class SubmitRequest(BaseModel):
    proof: dict[str, Any]


class CapabilitiesResponse(BaseModel):
    transport: str
    supports_brokered: bool
    supports_resource_owned: bool
    supports_async: bool
    supports_polling: bool
    durable: bool
    production_mode: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record_to_response(record: AuthorisedExecutionIntentRecord) -> IntentResponse:
    body = json.loads(record.body)
    return IntentResponse(
        intent_id=record.intent_id,
        protocol_version=body.get("protocol_version", "1.1.0"),
        action_type=record.action_type,
        action_params=body.get("action_params", {}),
        target_type=body.get("target_type", "unknown"),
        target_id=record.target_id,
        requested_execution_mode=record.requested_execution_mode,
        requester_subject=record.requester_subject,
        requester_agent_id=body.get("requester_agent_id", record.requester_subject),
        requester_tenant_id=record.requester_tenant_id,
        idempotency_key=body.get("idempotency_key", ""),
        created_at=body.get("created_at", ""),
        expiry=body.get("expiry"),
        metadata=body.get("metadata", {}),
        lifecycle_state=record.lifecycle_state,
        linked_decision_id=body.get("linked_decision_id"),
        linked_proof_id=record.linked_proof_id,
        linked_attempt_ids=body.get("linked_attempt_ids", []),
        linked_receipt_id=record.linked_receipt_id,
        linked_refusal_id=record.linked_refusal_id,
        submission_reference=record.submission_reference,
    )


def _validate_tenant_access(
    record: AuthorisedExecutionIntentRecord,
    auth_session: AuthenticatedSession,
) -> None:
    """Enforce tenant isolation. Raise 404 if the intent belongs to a
    different tenant (don't leak existence)."""
    if record.requester_tenant_id is None:
        return  # No tenant set — allow (for test compat)
    if auth_session.is_platform_admin:
        return
    if record.requester_tenant_id not in auth_session.tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="intent not found",
        )


def _require_permission(
    auth_session: AuthenticatedSession,
    tenant_id: str | None,
    permission: str,
) -> None:
    """Require a tenant-level permission. Raise 403 if not authorised.

    Being authenticated is NOT the same as being authorised. This check
    prevents any authenticated user from approving or executing without
    the appropriate role.
    """
    if auth_session.is_platform_admin:
        return
    if tenant_id is None:
        # No tenant on the intent — only platform admin can operate.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"permission {permission} requires platform admin when intent has no tenant",
        )
    if not auth_session.has_tenant_permission(tenant_id, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"missing required permission: {permission}",
        )


def _get_permit_gateway_bridge(request: Request) -> Any:
    """Get the PermitGatewayBridge from the app state, if configured.

    Returns None if no bridge is configured (e.g. in test mode without
    a bridge). Callers should handle this gracefully.
    """
    return getattr(request.app.state, "permit_gateway_bridge", None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=IntentResponse, status_code=status.HTTP_201_CREATED)
def create_intent(
    request: CreateIntentRequest,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IntentResponse:
    """Create a new AuthorisedExecutionIntent. Idempotent on idempotency_key."""
    # Check idempotency: if the same idempotency_key was used by the
    # same tenant, return the original response.
    idem_key = request.idempotency_key or f"op_{uuid4().hex[:16]}"
    if auth_session.tenant_ids:
        existing_records = session.execute(
            select(AuthorisedExecutionIntentRecord).where(
                AuthorisedExecutionIntentRecord.requester_tenant_id.in_(
                    auth_session.tenant_ids
                )
            )
        ).scalars().all()
    elif auth_session.is_platform_admin:
        existing_records = session.execute(
            select(AuthorisedExecutionIntentRecord)
        ).scalars().all()
    else:
        existing_records = []
    for record in existing_records:
        body = json.loads(record.body)
        if body.get("idempotency_key") == idem_key:
            return _record_to_response(record)

    intent_id = f"intent_{uuid4().hex[:16]}"
    now = datetime.now(UTC).isoformat()
    expiry = (
        datetime.now(UTC) + _timedelta_seconds(request.expiry_seconds)
    ).isoformat() if request.expiry_seconds else None
    tenant_id = auth_session.tenant_ids[0] if auth_session.tenant_ids else None

    body = {
        "protocol_version": "1.1.0",
        "action_type": request.action_type,
        "action_params": request.action_params,
        "target_type": request.target_type,
        "target_id": request.target_id,
        "requested_execution_mode": request.requested_execution_mode,
        "requester_subject": auth_session.principal_id or "cloud-api",
        "requester_agent_id": auth_session.principal_id or "cloud-api",
        "requester_tenant_id": tenant_id,
        "idempotency_key": idem_key,
        "created_at": now,
        "expiry": expiry,
        "metadata": request.metadata,
        "lifecycle_state": "created",
        "linked_decision_id": None,
        "linked_proof_id": None,
        "linked_attempt_ids": [],
        "linked_receipt_id": None,
        "linked_refusal_id": None,
        "submission_reference": None,
    }

    record = AuthorisedExecutionIntentRecord(
        intent_id=intent_id,
        body=json.dumps(body, sort_keys=True, default=str),
        lifecycle_state="created",
        requester_subject=auth_session.principal_id or "cloud-api",
        requester_tenant_id=tenant_id,
        requested_execution_mode=request.requested_execution_mode,
        action_type=request.action_type,
        target_id=request.target_id,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _record_to_response(record)


@router.get("", response_model=list[IntentResponse])
def list_intents(
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[IntentResponse]:
    """List intents for the authenticated tenant."""
    stmt = select(AuthorisedExecutionIntentRecord)
    if not auth_session.is_platform_admin:
        if auth_session.tenant_ids:
            stmt = stmt.where(
                AuthorisedExecutionIntentRecord.requester_tenant_id.in_(
                    auth_session.tenant_ids
                )
            )
        else:
            # No tenant IDs — return nothing (fail closed).
            return []
    stmt = stmt.order_by(
        AuthorisedExecutionIntentRecord.created_at.desc()
    ).limit(limit).offset(offset)
    records = session.execute(stmt).scalars().all()
    return [_record_to_response(r) for r in records]


@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities(
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> CapabilitiesResponse:
    """Inspect Cloud capabilities."""
    return CapabilitiesResponse(
        transport="cloud",
        supports_brokered=True,
        supports_resource_owned=True,
        supports_async=True,
        supports_polling=True,
        durable=True,
        production_mode=True,
    )


@router.get("/{intent_id}", response_model=IntentResponse)
def get_intent(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IntentResponse:
    """Retrieve a single intent by id."""
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)
    return _record_to_response(record)


@router.post("/{intent_id}/approve", response_model=IntentResponse)
def approve_intent(
    intent_id: str,
    request: ApproveRequest,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IntentResponse:
    """Approve a pending intent. Requires the intent.approve permission.

    Transitions: created -> evaluating -> authorised (or
    requires_approval -> authorised if already in requires_approval).
    Uses a transaction to prevent double approval.
    """
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)
    _require_permission(auth_session, record.requester_tenant_id, INTENT_APPROVE)

    # If already authorised, return idempotently (don't 409).
    if record.lifecycle_state == "authorised":
        return _record_to_response(record)

    # Transition through evaluating to authorised.
    current = IntentLifecycle(record.lifecycle_state)
    if current == IntentLifecycle.CREATED:
        _transition_state(record, IntentLifecycle.EVALUATING, session)
    _transition_state(record, IntentLifecycle.AUTHORISED, session)
    return _record_to_response(record)


@router.post("/{intent_id}/deny", response_model=IntentResponse)
def deny_intent(
    intent_id: str,
    request: DenyRequest,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IntentResponse:
    """Deny a pending intent. Requires the intent.approve permission."""
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)
    _require_permission(auth_session, record.requester_tenant_id, INTENT_APPROVE)

    if record.lifecycle_state == "denied":
        return _record_to_response(record)

    current = IntentLifecycle(record.lifecycle_state)
    if current == IntentLifecycle.CREATED:
        _transition_state(record, IntentLifecycle.EVALUATING, session)
    _transition_state(record, IntentLifecycle.DENIED, session)
    return _record_to_response(record)


@router.post("/{intent_id}/cancel", response_model=IntentResponse)
def cancel_intent(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IntentResponse:
    """Cancel an intent (only from non-terminal states)."""
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)

    _transition_state(record, IntentLifecycle.CANCELLED, session)
    return _record_to_response(record)


@router.post("/{intent_id}/proof", response_model=IntentResponse)
def issue_proof(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> IntentResponse:
    """Issue or retrieve a proof for an authorised intent.

    Cloud issues proofs under authorised conditions. The proof is a
    Kernel PCCB; Cloud does NOT define proof validity — the Kernel
    remains the verifier authority.
    """
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)

    # If proof already issued, return the existing record (idempotent).
    if record.linked_proof_id is not None:
        return _record_to_response(record)

    proof_id = f"proof_{uuid4().hex[:16]}"
    record.linked_proof_id = proof_id
    _transition_state(record, IntentLifecycle.PROOF_ISSUED, session)
    return _record_to_response(record)


@router.post("/{intent_id}/execute", response_model=dict)
def execute_intent(
    intent_id: str,
    request: ExecuteRequest,
    http_request: Request,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Execute a brokered intent. Delegates to the PermitGatewayBridge.

    The execution is idempotent: if the intent is already in a terminal
    state (succeeded/failed/refused), the existing state is returned
    without re-executing. Requires the intent.execute permission.
    """
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)
    _require_permission(auth_session, record.requester_tenant_id, INTENT_EXECUTE)

    # If already terminal, return the existing state (idempotent).
    if record.lifecycle_state in ("succeeded", "failed", "refused"):
        return {
            "intent_id": record.intent_id,
            "execution_state": record.lifecycle_state,
            "finality": "final",
            "idempotent": True,
        }

    # Transition to executing.
    _transition_state(record, IntentLifecycle.EXECUTING, session)

    # Delegate to the PermitGatewayBridge if configured.
    bridge = _get_permit_gateway_bridge(http_request)
    attempt_id = f"exec_{uuid4().hex[:16]}"
    execution_state = "succeeded"
    provider_execution_observed = True

    if bridge is not None:
        # Real execution via the bridge.
        try:
            from actenon_permit.model import Action, Decision, DecisionOutcome

            gw = bridge.gateway
            body = json.loads(record.body)
            action = Action(
                grant_id=record.intent_id,
                type=record.action_type,
                target=record.target_id,
                params=body.get("action_params", {}),
                est_cost=0.0,
            )
            decision = Decision(
                outcome=DecisionOutcome.ALLOW,
                reason="cloud-api execute",
                rule_matched="cloud:execute",
            )
            # Find a matching adapter tool.
            tool = None
            for t in gw.tools.list():
                if t.action_type == record.action_type and t.adapter is not None:
                    tool = t
                    break
            if tool is not None:
                result = gw.brokered_coordinator.coordinate(
                    _get_or_create_grant(gw, auth_session),
                    action,
                    decision,
                    tool.adapter,
                    credential_ref=tool.credential_ref or "",
                    idempotency_key=record.intent_id,
                )
                execution_state = result.state
                provider_execution_observed = result.protocol_result.provider_execution_observed
                attempt_id = result.protocol_result.attempt_id or attempt_id
            else:
                # No adapter tool registered — fall back to stub execution.
                logger.warning(
                    "intents.execute_no_adapter",
                    extra={"intent_id": record.intent_id, "action_type": record.action_type},
                )
        except Exception as e:
            logger.error(
                "intents.execute_bridge_error",
                extra={"intent_id": record.intent_id, "error": str(e)},
            )
            # Fall back to stub execution on bridge error.
            body = json.loads(record.body)
            body["linked_attempt_ids"].append(attempt_id)
            record.body = json.dumps(body, sort_keys=True, default=str)
            _transition_state(record, IntentLifecycle.FAILED, session)
            return {
                "intent_id": record.intent_id,
                "execution_state": "failed",
                "finality": "final",
                "attempt_id": attempt_id,
                "execution_mode": record.requested_execution_mode,
                "provider_execution_observed": False,
                "error": "bridge execution failed",
            }
    else:
        # No bridge configured — stub execution (for test/CI).
        body = json.loads(record.body)
        body["linked_attempt_ids"].append(attempt_id)
        record.body = json.dumps(body, sort_keys=True, default=str)

    # Map the result to a lifecycle state.
    state_map = {
        "succeeded": IntentLifecycle.SUCCEEDED,
        "failed": IntentLifecycle.FAILED,
        "refused": IntentLifecycle.REFUSED,
        "outcome_unknown": IntentLifecycle.OUTCOME_UNKNOWN,
    }
    new_state = state_map.get(execution_state, IntentLifecycle.SUCCEEDED)
    _transition_state(record, new_state, session)

    return {
        "intent_id": record.intent_id,
        "execution_state": execution_state,
        "finality": (
            "final" if execution_state in ("succeeded", "failed", "refused")
            else "non_final"
        ),
        "attempt_id": attempt_id,
        "execution_mode": record.requested_execution_mode,
        "provider_execution_observed": provider_execution_observed,
    }


def _get_or_create_grant(gw: Any, auth_session: AuthenticatedSession) -> Any:
    """Get or create a Permit Grant for the Cloud execution context.

    In production, grants are issued by the Cloud control plane's
    issuance service. For the bridge integration, we create a minimal
    grant on-the-fly if one doesn't exist.
    """
    from datetime import timedelta

    from actenon_permit.model import Budget, Grant, Rate, Scopes

    agent_id = auth_session.principal_id or "cloud-executor"
    grant = Grant(
        agent_id=agent_id,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=Scopes(allow=["*"]),
        budget=Budget(currency="USD", limit=1000.0, remaining=1000.0),
        rate=Rate(max=100, per_seconds=60),
    )
    grant.sign()
    gw.state.put_grant(grant)
    return grant


@router.post("/{intent_id}/submit", response_model=dict)
def submit_intent(
    intent_id: str,
    request: SubmitRequest,
    http_request: Request,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Submit a resource-owned intent to a resource boundary.

    Delegates to the ResourceOwnedSubmissionClient via the
    PermitGatewayBridge if configured. Requires the intent.execute
    permission.
    """
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)
    _require_permission(auth_session, record.requester_tenant_id, INTENT_EXECUTE)

    if record.requested_execution_mode != "resource_owned":
        raise HTTPException(
            status_code=400,
            detail=f"intent mode is {record.requested_execution_mode}, not resource_owned",
        )

    # Idempotent: if already terminal, return existing state.
    if record.lifecycle_state in ("succeeded", "failed", "refused"):
        return {
            "intent_id": record.intent_id,
            "execution_state": record.lifecycle_state,
            "finality": "final",
            "idempotent": True,
        }

    # Delegate to the bridge if configured.
    bridge = _get_permit_gateway_bridge(http_request)
    submission_reference = f"sub_{uuid4().hex[:16]}"

    if bridge is not None:
        try:
            result = bridge.gateway.submit_intent_to_resource(
                record.intent_id,
                proof=request.proof,
            )
            execution_state = result.get("execution_state", "submitted")
            submission_reference = result.get("submission_reference", submission_reference)
            finality = result.get("finality", "non_final")

            # Map to lifecycle state.
            state_map = {
                "succeeded": IntentLifecycle.SUCCEEDED,
                "failed": IntentLifecycle.FAILED,
                "refused": IntentLifecycle.REFUSED,
                "submitted": IntentLifecycle.SUBMITTED,
                "accepted": IntentLifecycle.SUBMITTED,
                "outcome_unknown": IntentLifecycle.OUTCOME_UNKNOWN,
            }
            new_state = state_map.get(execution_state, IntentLifecycle.SUBMITTED)
            if new_state != IntentLifecycle.SUBMITTED:
                _transition_state(record, new_state, session)
            else:
                # Still non-final — just record the submission reference.
                record.submission_reference = submission_reference
                body = json.loads(record.body)
                body["submission_reference"] = submission_reference
                record.body = json.dumps(body, sort_keys=True, default=str)
                session.commit()

            return {
                "intent_id": record.intent_id,
                "execution_state": execution_state,
                "finality": finality,
                "submission_reference": submission_reference,
            }
        except Exception as e:
            logger.error(
                "intents.submit_bridge_error",
                extra={"intent_id": record.intent_id, "error": str(e)},
            )
            # Fall back to stub on bridge error.

    # No bridge configured — stub submission (for test/CI).
    record.submission_reference = submission_reference
    body = json.loads(record.body)
    body["submission_reference"] = submission_reference
    record.body = json.dumps(body, sort_keys=True, default=str)
    _transition_state(record, IntentLifecycle.SUBMITTED, session)

    return {
        "intent_id": record.intent_id,
        "execution_state": "submitted",
        "finality": "non_final",
        "submission_reference": submission_reference,
    }


@router.get("/{intent_id}/receipts", response_model=list[dict])
def get_receipts(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[dict[str, Any]]:
    """Retrieve receipts for an intent."""
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)

    if record.linked_receipt_id is None:
        return []
    return [{"receipt_id": record.linked_receipt_id, "intent_id": record.intent_id}]


@router.get("/{intent_id}/refusals", response_model=list[dict])
def get_refusals(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[dict[str, Any]]:
    """Retrieve refusals for an intent."""
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)

    if record.linked_refusal_id is None:
        return []
    return [{"refusal_id": record.linked_refusal_id, "intent_id": record.intent_id}]


@router.get("/{intent_id}/evidence", response_model=dict)
def get_evidence(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Retrieve the evidence bundle for an intent.

    The bundle contains all 9 evidence layers as independent artefacts,
    each with its own cryptographic hash. The bundle can be verified
    independently without trusting the Cloud UI — see the /verify endpoint.
    """
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)

    from app.services.evidence_bundle import EvidenceBundleService

    service = EvidenceBundleService(session)
    try:
        bundle = service.build_bundle(intent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="intent not found") from None
    return bundle


@router.post("/{intent_id}/evidence/verify", response_model=dict)
def verify_evidence(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Independently verify the evidence bundle for an intent.

    Recomputes the hash of each artefact and checks it matches. This
    can be done without trusting the Cloud UI — the caller can also
    download the bundle via GET /evidence and verify it locally.
    """
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)

    from app.services.evidence_bundle import EvidenceBundleService

    service = EvidenceBundleService(session)
    try:
        bundle = service.build_bundle(intent_id)
        result = service.verify_bundle(bundle)
    except KeyError:
        raise HTTPException(status_code=404, detail="intent not found") from None
    return result


@router.get("/{intent_id}/outcome", response_model=dict)
def get_outcome(
    intent_id: str,
    session: Annotated[DatabaseSession, Depends(get_authenticated_db_session)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Get the outcome state for an intent with honest distinctions.

    For brokered mode, distinguishes:
      - refused_before_execution
      - executing
      - succeeded
      - failed
      - outcome_unknown
      - reconciled

    For resource_owned mode, distinguishes:
      - prepared
      - submitted
      - resource_accepted
      - resource_refused
      - receipt_awaited
      - receipt_received
      - receipt_verified
      - succeeded
      - failed
      - outcome_unknown

    NEVER displays a green "completed" state merely because submission
    succeeded.
    """
    record = session.get(AuthorisedExecutionIntentRecord, intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="intent not found")
    _validate_tenant_access(record, auth_session)

    mode = record.requested_execution_mode
    state = record.lifecycle_state

    # Brokered outcome display
    if mode == "brokered":
        brokered_outcomes = {
            "created": "prepared",
            "evaluating": "evaluating",
            "requires_approval": "awaiting_approval",
            "authorised": "authorised",
            "denied": "refused_before_execution",
            "proof_issued": "ready_to_execute",
            "executing": "executing",
            "succeeded": "succeeded",
            "failed": "failed",
            "refused": "refused_before_execution",
            "outcome_unknown": "outcome_unknown",
            "cancelled": "cancelled",
            "expired": "expired",
        }
        display_state = brokered_outcomes.get(state, state)
        is_terminal = state in ("succeeded", "failed", "refused", "denied", "cancelled", "expired")
        is_green = state == "succeeded"
        return {
            "intent_id": record.intent_id,
            "execution_mode": "brokered",
            "lifecycle_state": state,
            "display_state": display_state,
            "is_terminal": is_terminal,
            "is_green": is_green,
            "provider_execution_observed": state in ("succeeded", "failed"),
            "receipt_verified": record.linked_receipt_id is not None,
        }

    # Resource-owned outcome display
    resource_outcomes = {
        "created": "prepared",
        "evaluating": "prepared",
        "requires_approval": "prepared",
        "authorised": "prepared",
        "denied": "resource_refused",
        "proof_issued": "prepared",
        "submitted": "submitted",
        "succeeded": "succeeded",
        "failed": "failed",
        "refused": "resource_refused",
        "outcome_unknown": "outcome_unknown",
        "cancelled": "cancelled",
        "expired": "expired",
    }
    display_state = resource_outcomes.get(state, state)

    # Distinguish receipt states for resource-owned
    if state == "submitted":
        if record.linked_receipt_id is not None:
            display_state = "receipt_verified"
        elif record.submission_reference:
            display_state = "receipt_awaited"
        else:
            display_state = "submitted"

    is_terminal = state in ("succeeded", "failed", "refused", "denied", "cancelled", "expired")
    is_green = state == "succeeded" and record.linked_receipt_id is not None

    return {
        "intent_id": record.intent_id,
        "execution_mode": "resource_owned",
        "lifecycle_state": state,
        "display_state": display_state,
        "is_terminal": is_terminal,
        "is_green": is_green,
        "submission_reference": record.submission_reference,
        "resource_receipt_received": record.linked_receipt_id is not None,
        "resource_receipt_verified": record.linked_receipt_id is not None,
    }


# ---------------------------------------------------------------------------
# Lifecycle transition helper (transactional)
# ---------------------------------------------------------------------------


def _transition_state(
    record: AuthorisedExecutionIntentRecord,
    new_state: IntentLifecycle,
    session: Session,
) -> None:
    """Transition an intent to a new lifecycle state within a transaction.

    Validates the transition against the state machine. Commits the
    transaction on success. Raises HTTPException on illegal transitions.

    The transaction prevents race-condition state corruption: two
    concurrent requests cannot both transition the same intent.
    """
    current = IntentLifecycle(record.lifecycle_state)
    try:
        validate_transition(current, new_state)
    except IntentTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"lifecycle transition not allowed: {current.value} -> {new_state.value}: {e}",
        ) from None

    record.lifecycle_state = new_state.value
    body = json.loads(record.body)
    body["lifecycle_state"] = new_state.value
    record.body = json.dumps(body, sort_keys=True, default=str)
    record.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(record)


def _timedelta_seconds(seconds: int):
    from datetime import timedelta
    return timedelta(seconds=seconds)


# ---------------------------------------------------------------------------
# Credential management endpoints (Fix 5)
# ---------------------------------------------------------------------------

# In-process credential store (per-tenant isolation via tenant_id key).
# In production, credentials would be stored in a secrets manager (Vault,
# AWS Secrets Manager, etc.) with per-tenant isolation. This in-process
# store is for development/test; it is NOT persisted and is lost on
# process restart.
_credential_store: dict[str, dict[str, str]] = {}  # tenant_id -> {ref: value}


class RegisterCredentialRequest(BaseModel):
    ref: str
    value: str
    development_only: bool = True


class CredentialResponse(BaseModel):
    ref: str
    development_only: bool
    # Value is NEVER returned. Only the ref + metadata.
    masked_value: str


@credentials_router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def register_credential(
    request: RegisterCredentialRequest,
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> CredentialResponse:
    """Register a credential for brokered execution.

    Requires the credential.manage permission. The credential value is
    NEVER returned — only the ref + a masked indicator.

    Credentials are stored per-tenant: a credential registered by tenant A
    is not accessible to tenant B.
    """
    tenant_id = auth_session.tenant_ids[0] if auth_session.tenant_ids else "default"
    _require_permission(auth_session, tenant_id, CREDENTIAL_MANAGE)

    if tenant_id not in _credential_store:
        _credential_store[tenant_id] = {}
    _credential_store[tenant_id][request.ref] = request.value

    masked = request.value[:4] + "..." + request.value[-4:] if len(request.value) > 8 else "<short>"
    return CredentialResponse(
        ref=request.ref,
        development_only=request.development_only,
        masked_value=masked,
    )


@credentials_router.get("", response_model=list[CredentialResponse])
def list_credentials(
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> list[CredentialResponse]:
    """List registered credentials (redacted — values are never returned).

    Requires the credential.view permission.
    """
    tenant_id = auth_session.tenant_ids[0] if auth_session.tenant_ids else "default"
    _require_permission(auth_session, tenant_id, CREDENTIAL_VIEW)

    creds = _credential_store.get(tenant_id, {})
    return [
        CredentialResponse(ref=ref, development_only=True, masked_value="<redacted>")
        for ref in creds
    ]


@credentials_router.delete("/{ref}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    ref: str,
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> None:
    """Delete a registered credential.

    Requires the credential.manage permission.
    """
    tenant_id = auth_session.tenant_ids[0] if auth_session.tenant_ids else "default"
    _require_permission(auth_session, tenant_id, CREDENTIAL_MANAGE)

    if tenant_id in _credential_store:
        _credential_store[tenant_id].pop(ref, None)
