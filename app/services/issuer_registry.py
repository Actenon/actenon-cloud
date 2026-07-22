from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.metrics import get_metrics_registry
from app.models import (
    IssuerRegistryAuditEvent,
    IssuerRegistryRecord,
    IssuerStanding,
    IssuerStatusPublicationRecord,
    IssuerStatusPublicationStatus,
)
from app.services.countersigning import (
    CounterSigningService,
    ManagedIssuerStatusSignature,
    PrincipalContext,
)
from app.services.countersigning_format import normalize_utc, sha256_hex
from app.services.issuer_status_format import (
    build_issuer_status_artifact,
    build_issuer_status_statement,
    canonicalize_bytes,
    validate_party,
)

ISSUER_REGISTER_PERMISSION = "issuer_registry.register"
ISSUER_STATUS_MANAGE_PERMISSION = "issuer_registry.status.manage"
ISSUER_REVOKE_PERMISSION = "issuer_registry.revoke"
ISSUER_STATUS_PUBLISH_PERMISSION = "issuer_registry.status.publish"
ISSUER_REGISTRY_ADMIN_PERMISSIONS = frozenset(
    {
        ISSUER_REGISTER_PERMISSION,
        ISSUER_STATUS_MANAGE_PERMISSION,
        ISSUER_REVOKE_PERMISSION,
        ISSUER_STATUS_PUBLISH_PERMISSION,
    }
)


class IssuerRegistryError(RuntimeError):
    pass


class IssuerRegistryAuthorizationError(IssuerRegistryError):
    pass


class IssuerRegistryConflictError(IssuerRegistryError):
    pass


class IssuerRegistryConfigurationError(IssuerRegistryError):
    pass


class IssuerRegistryNotFoundError(IssuerRegistryError):
    pass


class IssuerRegistryStateError(IssuerRegistryError):
    pass


@dataclass(frozen=True, slots=True)
class IssuerRegistryActor:
    principal_type: str
    principal_id: str
    permissions: frozenset[str] = frozenset()


class IssuerStatusSigner(Protocol):
    def sign(
        self,
        statement: Mapping[str, Any],
        *,
        idempotency_token: str,
    ) -> ManagedIssuerStatusSignature: ...


class CounterSigningIssuerStatusSigner:
    """Uses the P10 managed signing service without exposing private key material."""

    def __init__(
        self,
        service: CounterSigningService,
        *,
        authority: PrincipalContext,
    ) -> None:
        self._service = service
        self._authority = authority

    def sign(
        self,
        statement: Mapping[str, Any],
        *,
        idempotency_token: str,
    ) -> ManagedIssuerStatusSignature:
        return self._service.sign_issuer_status(
            statement,
            authority=self._authority,
            idempotency_token=idempotency_token,
        )


@dataclass(frozen=True, slots=True)
class IssuerStatusPublicationResult:
    artifact: dict[str, Any]
    publication: IssuerStatusPublicationRecord


@dataclass(frozen=True, slots=True)
class IssuerRevocationResult:
    issuer: IssuerRegistryRecord
    publication: IssuerStatusPublicationResult


class IssuerRegistryService:
    def __init__(
        self,
        session: Session,
        *,
        status_authority: Mapping[str, Any],
        status_signer: IssuerStatusSigner | None = None,
        clock: Callable[[], datetime] | None = None,
        artifact_ttl_seconds: int = 300,
        max_staleness_seconds: int = 300,
    ) -> None:
        if artifact_ttl_seconds <= 0:
            raise IssuerRegistryConfigurationError(
                "issuer-status artifact TTL must be positive"
            )
        if max_staleness_seconds <= 0:
            raise IssuerRegistryConfigurationError(
                "issuer-status max staleness must be positive"
            )
        if artifact_ttl_seconds > max_staleness_seconds:
            raise IssuerRegistryConfigurationError(
                "issuer-status artifact TTL must not exceed max staleness"
            )
        self.session = session
        self.status_authority = validate_party(
            status_authority,
            field_name="status_authority",
        )
        self.status_signer = status_signer
        self.clock = clock or (lambda: datetime.now(UTC))
        self.artifact_ttl_seconds = artifact_ttl_seconds
        self.max_staleness_seconds = max_staleness_seconds

    def register_issuer(
        self,
        identity: Mapping[str, Any],
        *,
        actor: IssuerRegistryActor,
        registry_metadata: Mapping[str, Any] | None = None,
    ) -> IssuerRegistryRecord:
        self._authorize(actor, ISSUER_REGISTER_PERMISSION)
        issuer = validate_party(identity, field_name="issuer")
        existing = self._find_by_identity(issuer["type"], issuer["id"])
        if existing is not None:
            raise IssuerRegistryConflictError(
                f"issuer '{issuer['type']}:{issuer['id']}' is already registered"
            )
        now = self._now()
        record = IssuerRegistryRecord(
            registry_id=uuid4().hex,
            issuer_type=issuer["type"],
            issuer_id=issuer["id"],
            display_name=issuer.get("display_name"),
            standing=IssuerStanding.good_standing,
            standing_reason="registered in good standing",
            status_version=1,
            registry_metadata=dict(registry_metadata or {}),
            registered_at=now,
            standing_changed_at=now,
        )
        self.session.add(record)
        self._add_audit_event(
            record,
            event_type="issuer.registered",
            actor=actor,
            reason=record.standing_reason,
            prior_state=None,
            resulting_state=self._state_snapshot(record),
        )
        self.session.commit()
        self.session.refresh(record)
        self._record_transition_metric(record.standing)
        return record

    def suspend_issuer(
        self,
        registry_id: str,
        *,
        reason: str,
        actor: IssuerRegistryActor,
    ) -> IssuerRegistryRecord:
        return self._change_standing(
            registry_id,
            target=IssuerStanding.suspended,
            reason=reason,
            actor=actor,
            permission=ISSUER_STATUS_MANAGE_PERMISSION,
        )

    def reinstate_issuer(
        self,
        registry_id: str,
        *,
        reason: str,
        actor: IssuerRegistryActor,
    ) -> IssuerRegistryRecord:
        record = self._locked_record(registry_id)
        if record.standing == IssuerStanding.revoked:
            raise IssuerRegistryStateError(
                "a revoked issuer cannot be reinstated; register a new issuer identity"
            )
        return self._change_standing(
            registry_id,
            target=IssuerStanding.good_standing,
            reason=reason,
            actor=actor,
            permission=ISSUER_STATUS_MANAGE_PERMISSION,
        )

    def revoke_issuer(
        self,
        registry_id: str,
        *,
        reason: str,
        actor: IssuerRegistryActor,
    ) -> IssuerRevocationResult:
        issuer = self._change_standing(
            registry_id,
            target=IssuerStanding.revoked,
            reason=reason,
            actor=actor,
            permission=ISSUER_REVOKE_PERMISSION,
        )
        # The revocation state is committed before signing. A publication outage
        # therefore cannot roll the registry back to good standing.
        publication = self.publish_status(registry_id, actor=actor)
        return IssuerRevocationResult(issuer=issuer, publication=publication)

    def publish_status(
        self,
        registry_id: str,
        *,
        actor: IssuerRegistryActor,
    ) -> IssuerStatusPublicationResult:
        self._authorize(actor, ISSUER_STATUS_PUBLISH_PERMISSION)
        if self.status_signer is None:
            raise IssuerRegistryConfigurationError(
                "issuer-status signer is not configured"
            )
        issuer = self._locked_record(registry_id)
        publication_id = uuid4().hex
        status_reference = (
            f"issuer-status:{issuer.registry_id}:"
            f"v{issuer.status_version}:{publication_id}"
        )
        publication = IssuerStatusPublicationRecord(
            publication_id=publication_id,
            issuer_registry_id=issuer.registry_id,
            status_version=issuer.status_version,
            standing=issuer.standing,
            status=IssuerStatusPublicationStatus.requested,
            status_reference=status_reference,
            actor_principal_type=actor.principal_type,
            actor_principal_id=actor.principal_id,
            max_staleness_seconds=self.max_staleness_seconds,
        )
        self.session.add(publication)
        self.session.commit()

        issued_at = self._now()
        expires_at = issued_at + timedelta(seconds=self.artifact_ttl_seconds)
        statement = build_issuer_status_statement(
            issuer=issuer.identity(),
            authority=self.status_authority,
            status=issuer.standing.value,
            issued_at=issued_at,
            expires_at=expires_at,
            status_reference=status_reference,
        )
        signing_input_digest = sha256_hex(canonicalize_bytes(statement))

        try:
            signed = self.status_signer.sign(
                statement,
                idempotency_token=publication_id,
            )
            current = self._locked_record(registry_id)
            if (
                current.status_version != publication.status_version
                or current.standing != publication.standing
            ):
                raise IssuerRegistryStateError(
                    "issuer standing changed during publication; discard and retry"
                )
            artifact = build_issuer_status_artifact(
                statement=statement,
                key_id=signed.key_id,
                signature=signed.signature,
            )
        except Exception as exc:
            publication.status = IssuerStatusPublicationStatus.failed
            publication.signing_input_digest = signing_input_digest
            publication.error_code = exc.__class__.__name__
            publication.error_detail = str(exc)
            publication.completed_at = self._now()
            self.session.add(publication)
            self._add_audit_event(
                issuer,
                event_type="issuer.status_publication_failed",
                actor=actor,
                reason=str(exc),
                prior_state=None,
                resulting_state=self._state_snapshot(issuer),
                details={
                    "publication_id": publication_id,
                    "status_version": publication.status_version,
                },
            )
            self.session.commit()
            self._record_publication_metric("failed")
            if isinstance(exc, IssuerRegistryError):
                raise
            raise IssuerRegistryConfigurationError(
                "issuer-status publication failed closed"
            ) from exc

        publication.status = IssuerStatusPublicationStatus.completed
        publication.key_id = signed.key_id
        publication.signing_input_digest = signing_input_digest
        publication.provider_operation_ref = signed.provider_operation_ref
        publication.status_artifact = artifact
        publication.issued_at = issued_at
        publication.expires_at = expires_at
        publication.completed_at = self._now()
        self.session.add(publication)
        self._add_audit_event(
            issuer,
            event_type="issuer.status_published",
            actor=actor,
            reason=issuer.standing_reason,
            prior_state=None,
            resulting_state=self._state_snapshot(issuer),
            details={
                "publication_id": publication_id,
                "status_version": publication.status_version,
                "key_id": signed.key_id,
                "expires_at": artifact["expires_at"],
            },
        )
        self.session.commit()
        self.session.refresh(publication)
        self._record_publication_metric("completed")
        return IssuerStatusPublicationResult(
            artifact=artifact,
            publication=publication,
        )

    def get_issuer(self, registry_id: str) -> IssuerRegistryRecord:
        record = self.session.get(IssuerRegistryRecord, registry_id)
        if record is None:
            raise IssuerRegistryNotFoundError(
                f"issuer registry record '{registry_id}' was not found"
            )
        return record

    def find_issuer(self, issuer_type: str, issuer_id: str) -> IssuerRegistryRecord:
        record = self._find_by_identity(issuer_type, issuer_id)
        if record is None:
            raise IssuerRegistryNotFoundError(
                f"issuer '{issuer_type}:{issuer_id}' was not found"
            )
        return record

    def list_issuers(self) -> list[IssuerRegistryRecord]:
        return list(
            self.session.scalars(
                select(IssuerRegistryRecord).order_by(
                    IssuerRegistryRecord.registered_at.asc(),
                    IssuerRegistryRecord.registry_id.asc(),
                )
            )
        )

    def latest_status_artifact(
        self,
        *,
        registry_id: str | None = None,
        issuer_type: str | None = None,
        issuer_id: str | None = None,
    ) -> dict[str, Any]:
        if registry_id is not None:
            issuer = self._locked_record(registry_id)
        elif issuer_type is not None and issuer_id is not None:
            issuer = self._locked_by_identity(issuer_type, issuer_id)
        else:
            raise ValueError(
                "registry_id or both issuer_type and issuer_id are required"
            )
        publication = self.session.scalar(
            select(IssuerStatusPublicationRecord)
            .where(
                IssuerStatusPublicationRecord.issuer_registry_id
                == issuer.registry_id,
                IssuerStatusPublicationRecord.status_version
                == issuer.status_version,
                IssuerStatusPublicationRecord.status
                == IssuerStatusPublicationStatus.completed,
            )
            .order_by(IssuerStatusPublicationRecord.completed_at.desc())
        )
        if (
            publication is None
            or publication.status_artifact is None
            or publication.expires_at is None
        ):
            raise IssuerRegistryConfigurationError(
                "no current signed issuer-status artifact is available"
            )
        if normalize_utc(publication.expires_at) <= self._now():
            raise IssuerRegistryConfigurationError(
                "the current issuer-status artifact has expired"
            )
        return dict(publication.status_artifact)

    def list_audit_events(
        self,
        registry_id: str,
    ) -> list[IssuerRegistryAuditEvent]:
        self.get_issuer(registry_id)
        return list(
            self.session.scalars(
                select(IssuerRegistryAuditEvent)
                .where(
                    IssuerRegistryAuditEvent.issuer_registry_id == registry_id
                )
                .order_by(IssuerRegistryAuditEvent.created_at.asc())
            )
        )

    def _change_standing(
        self,
        registry_id: str,
        *,
        target: IssuerStanding,
        reason: str,
        actor: IssuerRegistryActor,
        permission: str,
    ) -> IssuerRegistryRecord:
        self._authorize(actor, permission)
        if not reason.strip():
            raise IssuerRegistryStateError("issuer standing changes require a reason")
        record = self._locked_record(registry_id)
        if record.standing == IssuerStanding.revoked and target != IssuerStanding.revoked:
            raise IssuerRegistryStateError(
                "a revoked issuer cannot transition to another standing"
            )
        if record.standing == target:
            return record
        prior = self._state_snapshot(record)
        now = self._now()
        record.standing = target
        record.standing_reason = reason.strip()
        record.status_version += 1
        record.standing_changed_at = now
        if target == IssuerStanding.revoked:
            record.revoked_at = now
        self.session.add(record)
        self._add_audit_event(
            record,
            event_type=f"issuer.{target.value}",
            actor=actor,
            reason=reason.strip(),
            prior_state=prior,
            resulting_state=self._state_snapshot(record),
        )
        self.session.commit()
        self.session.refresh(record)
        self._record_transition_metric(target)
        return record

    def _locked_record(self, registry_id: str) -> IssuerRegistryRecord:
        record = self.session.scalar(
            select(IssuerRegistryRecord)
            .where(IssuerRegistryRecord.registry_id == registry_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise IssuerRegistryNotFoundError(
                f"issuer registry record '{registry_id}' was not found"
            )
        return record

    def _locked_by_identity(
        self,
        issuer_type: str,
        issuer_id: str,
    ) -> IssuerRegistryRecord:
        record = self.session.scalar(
            select(IssuerRegistryRecord)
            .where(
                IssuerRegistryRecord.issuer_type == issuer_type,
                IssuerRegistryRecord.issuer_id == issuer_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise IssuerRegistryNotFoundError(
                f"issuer '{issuer_type}:{issuer_id}' was not found"
            )
        return record

    def _find_by_identity(
        self,
        issuer_type: str,
        issuer_id: str,
    ) -> IssuerRegistryRecord | None:
        return self.session.scalar(
            select(IssuerRegistryRecord).where(
                IssuerRegistryRecord.issuer_type == issuer_type,
                IssuerRegistryRecord.issuer_id == issuer_id,
            )
        )

    def _add_audit_event(
        self,
        record: IssuerRegistryRecord,
        *,
        event_type: str,
        actor: IssuerRegistryActor,
        reason: str | None,
        prior_state: Mapping[str, Any] | None,
        resulting_state: Mapping[str, Any] | None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.session.add(
            IssuerRegistryAuditEvent(
                event_id=uuid4().hex,
                issuer_registry_id=record.registry_id,
                event_type=event_type,
                actor_principal_type=actor.principal_type,
                actor_principal_id=actor.principal_id,
                reason=reason,
                prior_state=dict(prior_state) if prior_state is not None else None,
                resulting_state=(
                    dict(resulting_state) if resulting_state is not None else None
                ),
                details=dict(details or {}),
                created_at=self._now(),
            )
        )

    @staticmethod
    def _state_snapshot(record: IssuerRegistryRecord) -> dict[str, Any]:
        return {
            "issuer": record.identity(),
            "standing": record.standing.value,
            "standing_reason": record.standing_reason,
            "status_version": record.status_version,
        }

    @staticmethod
    def _authorize(actor: IssuerRegistryActor, permission: str) -> None:
        if permission not in actor.permissions:
            raise IssuerRegistryAuthorizationError(
                f"principal lacks {permission}"
            )

    def _now(self) -> datetime:
        return normalize_utc(self.clock()).replace(microsecond=0)

    @staticmethod
    def _record_transition_metric(standing: IssuerStanding) -> None:
        get_metrics_registry().counter(
            "action_control_plane_issuer_registry_transitions_total",
            "Issuer registry standing transitions.",
            label_names=("standing",),
        ).inc(standing=standing.value)

    @staticmethod
    def _record_publication_metric(outcome: str) -> None:
        get_metrics_registry().counter(
            "action_control_plane_issuer_status_publications_total",
            "Issuer-status publication attempts.",
            label_names=("outcome",),
        ).inc(outcome=outcome)


__all__ = [
    "ISSUER_REGISTER_PERMISSION",
    "ISSUER_REGISTRY_ADMIN_PERMISSIONS",
    "ISSUER_REVOKE_PERMISSION",
    "ISSUER_STATUS_MANAGE_PERMISSION",
    "ISSUER_STATUS_PUBLISH_PERMISSION",
    "CounterSigningIssuerStatusSigner",
    "IssuerRegistryActor",
    "IssuerRegistryAuthorizationError",
    "IssuerRegistryConflictError",
    "IssuerRegistryConfigurationError",
    "IssuerRegistryError",
    "IssuerRegistryNotFoundError",
    "IssuerRegistryService",
    "IssuerRegistryStateError",
    "IssuerRevocationResult",
    "IssuerStatusPublicationResult",
    "IssuerStatusSigner",
]
