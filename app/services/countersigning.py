from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CounterSigningKey,
    CounterSigningKeyStatus,
    CounterSigningLifecycleAction,
    CounterSigningLifecycleRecord,
    CounterSigningLifecycleStatus,
    CounterSigningOperationRecord,
    CounterSigningOperationStatus,
)
from app.services.countersigning_format import (
    COUNTERSIGNATURE_KEY_USE,
    build_countersignature_artifact,
    build_signed_statement,
    canonicalize_bytes,
    format_timestamp,
    normalize_utc,
    resolve_receipt_digest,
    sha256_hex,
    validate_witness,
)
from app.services.countersigning_provider import (
    CounterSigningProviderError,
    ManagedCounterSigningProvider,
    ManagedKeyDescriptor,
)
from app.services.issuer_status_format import (
    ISSUER_STATUS_KEY_USE,
    validate_issuer_status_statement,
)
from app.services.issuer_status_format import (
    canonicalize_bytes as canonicalize_issuer_status_bytes,
)
from app.services.key_set_publisher import (
    KeySetPublicationError,
    KeySetPublisher,
    PublishedKeySet,
)
from app.services.transparency_format import (
    CHECKPOINT_KEY_USE,
    validate_checkpoint_statement,
)
from app.services.transparency_format import (
    canonicalize_bytes as canonicalize_transparency_bytes,
)

SIGN_PERMISSION = "counter_signature.sign"
CHECKPOINT_SIGN_PERMISSION = "transparency_log.checkpoint.sign"
ISSUER_STATUS_SIGN_PERMISSION = "issuer_status.sign"
KEY_APPROVAL_PERMISSION = "counter_signature.keys.approve"
KEY_PROVISION_PERMISSION = "counter_signature.keys.provision"
KEY_ROTATE_PERMISSION = "counter_signature.keys.rotate"
KEY_REVOKE_PERMISSION = "counter_signature.keys.revoke"
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")


class CounterSigningError(RuntimeError):
    pass


class CounterSigningAuthorizationError(CounterSigningError):
    pass


class CounterSigningConfigurationError(CounterSigningError):
    pass


class CounterSigningKeyStateError(CounterSigningError):
    pass


@dataclass(frozen=True, slots=True)
class PrincipalContext:
    principal_type: str
    principal_id: str
    permissions: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class LifecycleAuthorization:
    requester: PrincipalContext
    approvers: tuple[PrincipalContext, ...]


@dataclass(frozen=True, slots=True)
class CounterSigningOutcome:
    artifact: dict[str, Any]
    operation: CounterSigningOperationRecord


@dataclass(frozen=True, slots=True)
class ManagedCheckpointSignature:
    key_id: str
    signature: bytes
    provider_operation_ref: str


@dataclass(frozen=True, slots=True)
class ManagedIssuerStatusSignature:
    key_id: str
    signature: bytes
    provider_operation_ref: str


class CounterSigningService:
    def __init__(
        self,
        session: Session,
        *,
        provider: ManagedCounterSigningProvider,
        key_set_publisher: KeySetPublisher,
        witness: Mapping[str, Any],
        origin: str,
        clock: Callable[[], datetime] | None = None,
        minimum_lifecycle_approvals: int = 2,
        key_set_cache_max_age_seconds: int = 300,
    ) -> None:
        if not origin.startswith("https://") or origin.endswith("/"):
            raise CounterSigningConfigurationError(
                "counter-signing origin must be an HTTPS origin without a trailing slash"
            )
        if minimum_lifecycle_approvals < 2:
            raise CounterSigningConfigurationError(
                "counter-signing key lifecycle requires at least two approvers"
            )
        if key_set_cache_max_age_seconds < 0:
            raise CounterSigningConfigurationError("key-set cache max age must be non-negative")

        self.session = session
        self.provider = provider
        self.key_set_publisher = key_set_publisher
        self.witness = validate_witness(witness)
        self.origin = origin
        self.clock = clock or (lambda: datetime.now(UTC))
        self.minimum_lifecycle_approvals = minimum_lifecycle_approvals
        self.key_set_cache_max_age_seconds = key_set_cache_max_age_seconds

    def counter_sign(
        self,
        receipt_or_digest: Any,
        *,
        authority: PrincipalContext,
        tenant_id: str | None = None,
        receipt_id: str | None = None,
        anchor_reference: Mapping[str, Any] | None = None,
    ) -> CounterSigningOutcome:
        receipt_digest = resolve_receipt_digest(receipt_or_digest)
        key = self._active_key()
        operation = CounterSigningOperationRecord(
            operation_id=uuid4().hex,
            tenant_id=tenant_id,
            receipt_id=receipt_id,
            receipt_digest=receipt_digest["value"],
            key_id=key.key_id if key is not None else None,
            actor_principal_type=authority.principal_type,
            actor_principal_id=authority.principal_id,
            status=CounterSigningOperationStatus.requested,
        )
        self.session.add(operation)
        self.session.flush()

        try:
            self._authorize_signing(authority)
            if key is None:
                raise CounterSigningConfigurationError("no active counter-signing key is available")
        except CounterSigningError as exc:
            operation.status = CounterSigningOperationStatus.denied
            operation.error_code = exc.__class__.__name__
            operation.error_detail = str(exc)
            operation.completed_at = self._now()
            self.session.add(operation)
            self.session.commit()
            raise

        signed_at = format_timestamp(self._now())
        statement = build_signed_statement(
            receipt_digest=receipt_digest,
            witness=self.witness,
            signed_at=signed_at,
            anchor_reference=anchor_reference,
        )
        signing_input = canonicalize_bytes(statement)
        operation.signing_input_digest = sha256_hex(signing_input)
        self.session.add(operation)

        try:
            provider_outcome = self.provider.sign(
                provider_key_ref=key.provider_key_ref,
                message=signing_input,
                idempotency_token=operation.operation_id,
            )
            if len(provider_outcome.signature) != 64:
                raise CounterSigningProviderError(
                    "managed provider returned an invalid Ed25519 signature length"
                )
        except Exception as exc:
            operation.status = CounterSigningOperationStatus.failed
            operation.error_code = "PROVIDER_SIGNING_FAILED"
            operation.error_detail = exc.__class__.__name__
            operation.completed_at = self._now()
            self.session.add(operation)
            self.session.commit()
            raise CounterSigningProviderError(
                "managed counter-signing provider failed closed"
            ) from exc

        artifact = build_countersignature_artifact(
            receipt_digest=receipt_digest,
            witness=self.witness,
            signed_at=signed_at,
            anchor_reference=anchor_reference,
            key_id=key.key_id,
            signature=provider_outcome.signature,
        )
        operation.status = CounterSigningOperationStatus.completed
        operation.provider_operation_ref = provider_outcome.provider_operation_ref
        operation.countersignature_artifact = artifact
        operation.completed_at = self._now()
        self.session.add(operation)
        self.session.commit()
        self.session.refresh(operation)
        return CounterSigningOutcome(artifact=artifact, operation=operation)

    def sign_transparency_checkpoint(
        self,
        statement: Mapping[str, Any],
        *,
        authority: PrincipalContext,
        idempotency_token: str,
    ) -> ManagedCheckpointSignature:
        """Sign only a validated P11 checkpoint statement through managed custody."""

        self._authorize_service_permission(
            authority,
            permission=CHECKPOINT_SIGN_PERMISSION,
            operation_name="transparency checkpoint signing",
        )
        key = self._active_key()
        if key is None:
            raise CounterSigningConfigurationError(
                "no active managed signing key is available"
            )
        validated = validate_checkpoint_statement(
            statement,
            expected_log_identity=self.witness,
        )
        signing_input = canonicalize_transparency_bytes(validated)
        try:
            provider_outcome = self.provider.sign(
                provider_key_ref=key.provider_key_ref,
                message=signing_input,
                idempotency_token=idempotency_token,
            )
            if len(provider_outcome.signature) != 64:
                raise CounterSigningProviderError(
                    "managed provider returned an invalid Ed25519 signature length"
                )
        except Exception as exc:
            raise CounterSigningProviderError(
                "managed transparency checkpoint signing failed closed"
            ) from exc
        return ManagedCheckpointSignature(
            key_id=key.key_id,
            signature=provider_outcome.signature,
            provider_operation_ref=provider_outcome.provider_operation_ref,
        )

    def sign_issuer_status(
        self,
        statement: Mapping[str, Any],
        *,
        authority: PrincipalContext,
        idempotency_token: str,
    ) -> ManagedIssuerStatusSignature:
        """Sign only a validated P12 issuer-status statement through managed custody."""

        self._authorize_service_permission(
            authority,
            permission=ISSUER_STATUS_SIGN_PERMISSION,
            operation_name="issuer-status signing",
        )
        key = self._active_key()
        if key is None:
            raise CounterSigningConfigurationError(
                "no active managed signing key is available"
            )
        validated = validate_issuer_status_statement(
            statement,
            expected_authority=self.witness,
        )
        signing_input = canonicalize_issuer_status_bytes(validated)
        try:
            provider_outcome = self.provider.sign(
                provider_key_ref=key.provider_key_ref,
                message=signing_input,
                idempotency_token=idempotency_token,
            )
            if len(provider_outcome.signature) != 64:
                raise CounterSigningProviderError(
                    "managed provider returned an invalid Ed25519 signature length"
                )
        except Exception as exc:
            raise CounterSigningProviderError(
                "managed issuer-status signing failed closed"
            ) from exc
        return ManagedIssuerStatusSignature(
            key_id=key.key_id,
            signature=provider_outcome.signature,
            provider_operation_ref=provider_outcome.provider_operation_ref,
        )

    def provision_initial_key(
        self,
        *,
        key_id: str,
        authorization: LifecycleAuthorization,
        expires_at: datetime | None = None,
        lifecycle_metadata: Mapping[str, Any] | None = None,
    ) -> CounterSigningKey:
        self._validate_key_id(key_id)
        if self._all_keys():
            raise CounterSigningKeyStateError(
                "initial provisioning requires an empty counter-signing key registry"
            )
        return self._provision_and_publish(
            action=CounterSigningLifecycleAction.provision,
            key_id=key_id,
            authorization=authorization,
            required_permission=KEY_PROVISION_PERMISSION,
            prior_key=None,
            expires_at=expires_at,
            lifecycle_metadata=lifecycle_metadata,
        )

    def rotate_key(
        self,
        *,
        new_key_id: str,
        authorization: LifecycleAuthorization,
        expires_at: datetime | None = None,
        lifecycle_metadata: Mapping[str, Any] | None = None,
    ) -> CounterSigningKey:
        self._validate_key_id(new_key_id)
        active_key = self._active_key()
        if active_key is None:
            raise CounterSigningKeyStateError("rotation requires an active counter-signing key")
        if self.session.get(CounterSigningKey, new_key_id) is not None:
            raise CounterSigningKeyStateError(
                f"counter-signing key_id '{new_key_id}' already exists"
            )
        return self._provision_and_publish(
            action=CounterSigningLifecycleAction.rotate,
            key_id=new_key_id,
            authorization=authorization,
            required_permission=KEY_ROTATE_PERMISSION,
            prior_key=active_key,
            expires_at=expires_at,
            lifecycle_metadata=lifecycle_metadata,
        )

    def revoke_key(
        self,
        *,
        key_id: str,
        reason: str,
        authorization: LifecycleAuthorization,
    ) -> CounterSigningKey:
        if not reason.strip():
            raise CounterSigningKeyStateError("key revocation requires a reason")
        key = self.session.get(CounterSigningKey, key_id)
        if key is None:
            raise CounterSigningKeyStateError(f"counter-signing key_id '{key_id}' was not found")
        if key.status == CounterSigningKeyStatus.revoked:
            raise CounterSigningKeyStateError("counter-signing key is already revoked")

        lifecycle = self._begin_lifecycle(
            action=CounterSigningLifecycleAction.revoke,
            target_key_id=key_id,
            prior_key_id=None,
            authorization=authorization,
        )
        lifecycle_snapshot = self._lifecycle_snapshot(lifecycle)
        try:
            self._authorize_lifecycle(
                authorization,
                required_permission=KEY_REVOKE_PERMISSION,
            )
        except CounterSigningAuthorizationError as exc:
            self._deny_lifecycle(lifecycle, exc)
            raise

        try:
            provider_outcome = self.provider.disable_key(
                provider_key_ref=key.provider_key_ref,
                reason=reason,
                idempotency_token=lifecycle.lifecycle_operation_id,
            )
            now = self._now()
            key.status = CounterSigningKeyStatus.revoked
            key.revoked_at = now
            key.lifecycle_metadata = {
                **dict(key.lifecycle_metadata),
                "revocation_reason": reason,
            }
            self.session.add(key)
            self.session.flush()
            publication = self._publish_current_key_set(
                now=now,
                version=self._publication_version(now, key_id, "revoke"),
            )
            lifecycle.status = CounterSigningLifecycleStatus.completed
            lifecycle.provider_operation_ref = provider_outcome.provider_operation_ref
            lifecycle.published_key_set_digest = publication.digest
            lifecycle.details = {
                "publication_reference": publication.publication_reference,
                "revoked_at": format_timestamp(now),
                "reason": reason,
            }
            lifecycle.completed_at = now
            self.session.add(lifecycle)
            self.session.commit()
            self.session.refresh(key)
            return key
        except Exception as exc:
            self.session.rollback()
            self._persist_lifecycle_failure(
                lifecycle_snapshot=lifecycle_snapshot,
                error_code="KEY_REVOCATION_FAILED",
                error=exc,
            )
            raise CounterSigningProviderError(
                "counter-signing key revocation failed closed"
            ) from exc

    def current_public_key_set(self) -> dict[str, Any]:
        return self._build_public_key_set(now=self._now())

    def list_signing_operations(self) -> list[CounterSigningOperationRecord]:
        return list(
            self.session.scalars(
                select(CounterSigningOperationRecord).order_by(
                    CounterSigningOperationRecord.created_at.asc()
                )
            )
        )

    def list_lifecycle_operations(self) -> list[CounterSigningLifecycleRecord]:
        return list(
            self.session.scalars(
                select(CounterSigningLifecycleRecord).order_by(
                    CounterSigningLifecycleRecord.created_at.asc()
                )
            )
        )

    def _provision_and_publish(
        self,
        *,
        action: CounterSigningLifecycleAction,
        key_id: str,
        authorization: LifecycleAuthorization,
        required_permission: str,
        prior_key: CounterSigningKey | None,
        expires_at: datetime | None,
        lifecycle_metadata: Mapping[str, Any] | None,
    ) -> CounterSigningKey:
        lifecycle = self._begin_lifecycle(
            action=action,
            target_key_id=key_id,
            prior_key_id=prior_key.key_id if prior_key is not None else None,
            authorization=authorization,
        )
        lifecycle_snapshot = self._lifecycle_snapshot(lifecycle)
        try:
            self._authorize_lifecycle(
                authorization,
                required_permission=required_permission,
            )
        except CounterSigningAuthorizationError as exc:
            self._deny_lifecycle(lifecycle, exc)
            raise

        try:
            now = self._now()
            if expires_at is not None and normalize_utc(expires_at) <= now:
                raise CounterSigningKeyStateError(
                    "counter-signing key expiry must be after activation"
                )
            descriptor = self.provider.provision_key(
                key_id=key_id,
                idempotency_token=lifecycle.lifecycle_operation_id,
                labels={
                    "actenon-purpose": COUNTERSIGNATURE_KEY_USE,
                    "actenon-kid": key_id,
                },
            )
            key = self._key_from_descriptor(
                descriptor,
                now=now,
                expires_at=expires_at,
                lifecycle_metadata=lifecycle_metadata,
            )
            if prior_key is not None:
                prior_key.status = CounterSigningKeyStatus.retired
                prior_key.retired_at = now
                prior_key.replaced_by_key_id = key.key_id
                self.session.add(prior_key)
            self.session.add(key)
            self.session.flush()

            publication = self._publish_current_key_set(
                now=now,
                version=self._publication_version(now, key_id, action.value),
            )
            lifecycle.status = CounterSigningLifecycleStatus.completed
            lifecycle.provider_operation_ref = descriptor.provider_operation_ref
            lifecycle.published_key_set_digest = publication.digest
            lifecycle.details = {
                "publication_reference": publication.publication_reference,
                "provider_attestation_ref": descriptor.provider_attestation_ref,
                "non_exportable": descriptor.non_exportable,
            }
            lifecycle.completed_at = now
            self.session.add(lifecycle)
            self.session.commit()
            self.session.refresh(key)
            return key
        except Exception as exc:
            self.session.rollback()
            self._persist_lifecycle_failure(
                lifecycle_snapshot=lifecycle_snapshot,
                error_code="KEY_PROVISION_OR_PUBLICATION_FAILED",
                error=exc,
            )
            if isinstance(exc, CounterSigningError):
                raise
            if isinstance(exc, (CounterSigningProviderError, KeySetPublicationError)):
                raise
            raise CounterSigningProviderError(
                "counter-signing key provisioning failed closed"
            ) from exc

    def _key_from_descriptor(
        self,
        descriptor: ManagedKeyDescriptor,
        *,
        now: datetime,
        expires_at: datetime | None,
        lifecycle_metadata: Mapping[str, Any] | None,
    ) -> CounterSigningKey:
        public_jwk = dict(descriptor.public_key_jwk)
        if {"d", "p", "q", "dp", "dq", "qi", "oth", "k"}.intersection(public_jwk):
            raise CounterSigningConfigurationError(
                "counter-signing provider returned private key material"
            )
        public_jwk.update(
            {
                "kid": descriptor.key_id,
                "alg": "EdDSA",
                "use": "sig",
            }
        )
        return CounterSigningKey(
            key_id=descriptor.key_id,
            provider_key_ref=descriptor.provider_key_ref,
            public_key_jwk=public_jwk,
            witness=dict(self.witness),
            origin=self.origin,
            status=CounterSigningKeyStatus.active,
            not_before=now,
            expires_at=normalize_utc(expires_at) if expires_at is not None else None,
            provider_attestation_ref=descriptor.provider_attestation_ref,
            lifecycle_metadata={
                **dict(lifecycle_metadata or {}),
                "custody": "external_hsm_or_kms",
                "non_exportable": descriptor.non_exportable,
            },
        )

    def _publish_current_key_set(
        self,
        *,
        now: datetime,
        version: str,
    ) -> PublishedKeySet:
        return self.key_set_publisher.publish(
            document=self._build_public_key_set(now=now),
            version=version,
        )

    def _build_public_key_set(self, *, now: datetime) -> dict[str, Any]:
        keys = self._all_keys()
        if not keys:
            raise CounterSigningConfigurationError(
                "cannot publish an empty counter-signing key set"
            )
        descriptors: list[dict[str, Any]] = []
        for key in keys:
            descriptor: dict[str, Any] = {
                "key_id": key.key_id,
                "algorithm": "EdDSA",
                "use": [
                    COUNTERSIGNATURE_KEY_USE,
                    CHECKPOINT_KEY_USE,
                    ISSUER_STATUS_KEY_USE,
                ],
                "status": ("active" if key.status == CounterSigningKeyStatus.active else "retired"),
                "not_before": format_timestamp(normalize_utc(key.not_before)),
                "public_key_jwk": dict(key.public_key_jwk),
            }
            if key.expires_at is not None:
                descriptor["expires_at"] = format_timestamp(normalize_utc(key.expires_at))
            if key.revoked_at is not None:
                descriptor["revoked_at"] = format_timestamp(normalize_utc(key.revoked_at))
            if key.replaced_by_key_id is not None:
                descriptor["replaced_by"] = key.replaced_by_key_id
            revocation_reason = dict(key.lifecycle_metadata).get("revocation_reason")
            if isinstance(revocation_reason, str) and revocation_reason:
                descriptor["revocation_reason"] = revocation_reason
            descriptors.append(descriptor)

        return {
            "contract": {"name": "key_discovery", "version": "v1"},
            "issuer": dict(self.witness),
            "origin": self.origin,
            "published_at": format_timestamp(now),
            "cache": {"max_age_seconds": self.key_set_cache_max_age_seconds},
            "keys": descriptors,
        }

    def _all_keys(self) -> list[CounterSigningKey]:
        return list(
            self.session.scalars(
                select(CounterSigningKey).order_by(
                    CounterSigningKey.not_before.asc(),
                    CounterSigningKey.key_id.asc(),
                )
            )
        )

    def _active_key(self) -> CounterSigningKey | None:
        keys = list(
            self.session.scalars(
                select(CounterSigningKey).where(
                    CounterSigningKey.status == CounterSigningKeyStatus.active
                )
            )
        )
        if len(keys) > 1:
            raise CounterSigningConfigurationError(
                "multiple active counter-signing keys are configured"
            )
        return keys[0] if keys else None

    def _begin_lifecycle(
        self,
        *,
        action: CounterSigningLifecycleAction,
        target_key_id: str,
        prior_key_id: str | None,
        authorization: LifecycleAuthorization,
    ) -> CounterSigningLifecycleRecord:
        lifecycle = CounterSigningLifecycleRecord(
            lifecycle_operation_id=uuid4().hex,
            action=action,
            status=CounterSigningLifecycleStatus.requested,
            target_key_id=target_key_id,
            prior_key_id=prior_key_id,
            requester_principal_type=authorization.requester.principal_type,
            requester_principal_id=authorization.requester.principal_id,
            approver_principal_ids=[approver.principal_id for approver in authorization.approvers],
        )
        self.session.add(lifecycle)
        self.session.flush()
        return lifecycle

    def _deny_lifecycle(
        self,
        lifecycle: CounterSigningLifecycleRecord,
        error: CounterSigningAuthorizationError,
    ) -> None:
        lifecycle.status = CounterSigningLifecycleStatus.denied
        lifecycle.error_code = error.__class__.__name__
        lifecycle.error_detail = str(error)
        lifecycle.completed_at = self._now()
        self.session.add(lifecycle)
        self.session.commit()

    def _persist_lifecycle_failure(
        self,
        *,
        lifecycle_snapshot: Mapping[str, Any],
        error_code: str,
        error: Exception,
    ) -> None:
        failed = CounterSigningLifecycleRecord(
            lifecycle_operation_id=lifecycle_snapshot["lifecycle_operation_id"],
            action=lifecycle_snapshot["action"],
            status=CounterSigningLifecycleStatus.failed,
            target_key_id=lifecycle_snapshot["target_key_id"],
            prior_key_id=lifecycle_snapshot["prior_key_id"],
            requester_principal_type=lifecycle_snapshot["requester_principal_type"],
            requester_principal_id=lifecycle_snapshot["requester_principal_id"],
            approver_principal_ids=list(lifecycle_snapshot["approver_principal_ids"]),
            error_code=error_code,
            error_detail=error.__class__.__name__,
            completed_at=self._now(),
        )
        self.session.add(failed)
        self.session.commit()

    @staticmethod
    def _lifecycle_snapshot(
        lifecycle: CounterSigningLifecycleRecord,
    ) -> dict[str, Any]:
        return {
            "lifecycle_operation_id": lifecycle.lifecycle_operation_id,
            "action": lifecycle.action,
            "target_key_id": lifecycle.target_key_id,
            "prior_key_id": lifecycle.prior_key_id,
            "requester_principal_type": lifecycle.requester_principal_type,
            "requester_principal_id": lifecycle.requester_principal_id,
            "approver_principal_ids": list(lifecycle.approver_principal_ids),
        }

    def _authorize_signing(self, authority: PrincipalContext) -> None:
        self._authorize_service_permission(
            authority,
            permission=SIGN_PERMISSION,
            operation_name="counter-signing",
        )

    @staticmethod
    def _authorize_service_permission(
        authority: PrincipalContext,
        *,
        permission: str,
        operation_name: str,
    ) -> None:
        if authority.principal_type != "service":
            raise CounterSigningAuthorizationError(
                f"{operation_name} may only be invoked by the dedicated service identity"
            )
        if permission not in authority.permissions:
            raise CounterSigningAuthorizationError(
                f"service identity lacks {permission}"
            )

    def _authorize_lifecycle(
        self,
        authorization: LifecycleAuthorization,
        *,
        required_permission: str,
    ) -> None:
        requester = authorization.requester
        if requester.principal_type != "user":
            raise CounterSigningAuthorizationError(
                "counter-signing key lifecycle requester must be an authenticated human"
            )
        if required_permission not in requester.permissions:
            raise CounterSigningAuthorizationError(f"requester lacks {required_permission}")

        unique_approvers = {approver.principal_id: approver for approver in authorization.approvers}
        if requester.principal_id in unique_approvers:
            raise CounterSigningAuthorizationError(
                "key lifecycle requester may not approve their own request"
            )
        if len(unique_approvers) < self.minimum_lifecycle_approvals:
            raise CounterSigningAuthorizationError(
                "key lifecycle operation does not have the required independent approvals"
            )
        for approver in unique_approvers.values():
            if approver.principal_type != "user":
                raise CounterSigningAuthorizationError(
                    "key lifecycle approvers must be authenticated humans"
                )
            if KEY_APPROVAL_PERMISSION not in approver.permissions:
                raise CounterSigningAuthorizationError(
                    f"approver '{approver.principal_id}' lacks {KEY_APPROVAL_PERMISSION}"
                )

    @staticmethod
    def _validate_key_id(key_id: str) -> None:
        if _KEY_ID_RE.fullmatch(key_id) is None:
            raise CounterSigningKeyStateError("key_id must be 1-256 URL-safe identifier characters")

    @staticmethod
    def _publication_version(now: datetime, key_id: str, action: str) -> str:
        return f"{now.strftime('%Y%m%dT%H%M%SZ')}-{action}-{key_id}"

    def _now(self) -> datetime:
        return normalize_utc(self.clock())


__all__ = [
    "CHECKPOINT_SIGN_PERMISSION",
    "ISSUER_STATUS_SIGN_PERMISSION",
    "KEY_APPROVAL_PERMISSION",
    "KEY_PROVISION_PERMISSION",
    "KEY_REVOKE_PERMISSION",
    "KEY_ROTATE_PERMISSION",
    "SIGN_PERMISSION",
    "CounterSigningAuthorizationError",
    "CounterSigningConfigurationError",
    "CounterSigningError",
    "CounterSigningKeyStateError",
    "CounterSigningOutcome",
    "CounterSigningService",
    "LifecycleAuthorization",
    "ManagedCheckpointSignature",
    "ManagedIssuerStatusSignature",
    "PrincipalContext",
]
