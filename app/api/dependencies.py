from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings
from app.container import ApplicationContainer
from app.database import set_session_rls_context
from app.services.action_intents import ActionIntentService, KernelContractRegistry
from app.services.approvals import ApprovalService
from app.services.audit import AuditService
from app.services.auth import AuthenticatedSession, AuthenticationError, AuthService
from app.services.escrow import EscrowService
from app.services.evidence import EvidenceService
from app.services.issuance import IssuanceService
from app.services.issuer_registry import IssuerRegistryService
from app.services.policy_engine import PolicyEngine, PolicyManagementService
from app.services.receipts import ReceiptService
from app.services.signing import SigningService
from app.services.transparency_log import TransparencyLogService
from app.services.usage import UsageService

bearer_scheme = HTTPBearer(auto_error=False)


def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container  # type: ignore[no-any-return]


def get_settings(container: Annotated[ApplicationContainer, Depends(get_container)]) -> Settings:
    return container.settings


def get_db_session(
    request: Request,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> Generator[Session, None, None]:
    with container.database.session() as session:
        request.state.db_session = session
        yield session


def get_contract_registry() -> KernelContractRegistry:
    return KernelContractRegistry()


def get_policy_management_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> PolicyManagementService:
    return PolicyManagementService(session)


def get_policy_engine() -> PolicyEngine:
    return PolicyEngine()


def get_approval_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ApprovalService:
    return ApprovalService(session)


def get_evidence_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvidenceService:
    return EvidenceService.from_settings(session, settings=settings)


def get_audit_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AuditService:
    return AuditService(session)


def get_usage_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> UsageService:
    return UsageService(session)


def get_auth_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(session, settings=settings)


def get_current_session(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        auth_session = auth_service.authenticate_bearer_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    db_session = getattr(request.state, "db_session", None)
    target_sessions: list[Session] = []
    if isinstance(db_session, Session):
        target_sessions.append(db_session)
    if not any(existing is auth_service.session for existing in target_sessions):
        target_sessions.append(auth_service.session)
    for session in target_sessions:
        set_session_rls_context(
            session,
            tenant_ids=auth_session.tenant_ids,
            principal_id=auth_session.principal_id,
            is_platform_admin=auth_session.is_platform_admin,
        )
    request.state.auth_session = auth_session
    return auth_session


def get_escrow_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EscrowService:
    return EscrowService(session, settings=settings)


def get_receipt_service(
    session: Annotated[Session, Depends(get_db_session)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> ReceiptService:
    return ReceiptService(session, audit_service=audit_service)


def get_transparency_log_service(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TransparencyLogService:
    signer = getattr(request.app.state, "transparency_checkpoint_signer", None)
    if signer is not None and not hasattr(signer, "sign"):
        raise RuntimeError("configured transparency checkpoint signer is invalid")
    return TransparencyLogService(
        session,
        log_identity={
            "type": settings.transparency_log_identity_type,
            "id": settings.transparency_log_id,
            "display_name": settings.transparency_log_display_name,
        },
        checkpoint_signer=signer,
    )


def get_issuer_registry_service(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IssuerRegistryService:
    signer = getattr(request.app.state, "issuer_status_signer", None)
    if signer is not None and not hasattr(signer, "sign"):
        raise RuntimeError("configured issuer-status signer is invalid")
    return IssuerRegistryService(
        session,
        status_authority={
            "type": settings.issuer_status_authority_type,
            "id": settings.issuer_status_authority_id,
            "display_name": settings.issuer_status_authority_display_name,
        },
        status_signer=signer,
        artifact_ttl_seconds=settings.issuer_status_ttl_seconds,
        max_staleness_seconds=settings.issuer_status_max_staleness_seconds,
    )


def get_signing_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SigningService:
    return SigningService(session, settings=settings)


def get_issuance_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    approval_service: Annotated[ApprovalService, Depends(get_approval_service)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
    signing_service: Annotated[SigningService, Depends(get_signing_service)],
) -> IssuanceService:
    return IssuanceService(
        session,
        settings=settings,
        approval_service=approval_service,
        evidence_service=evidence_service,
        signing_service=signing_service,
    )


def get_action_intent_service(
    session: Annotated[Session, Depends(get_db_session)],
    contract_registry: Annotated[KernelContractRegistry, Depends(get_contract_registry)],
    policy_service: Annotated[PolicyManagementService, Depends(get_policy_management_service)],
    policy_engine: Annotated[PolicyEngine, Depends(get_policy_engine)],
    approval_service: Annotated[ApprovalService, Depends(get_approval_service)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> ActionIntentService:
    return ActionIntentService(
        session,
        contract_registry=contract_registry,
        policy_service=policy_service,
        policy_engine=policy_engine,
        approval_service=approval_service,
        evidence_service=evidence_service,
    )
