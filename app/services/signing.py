from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    IssuedProof,
    SigningAlgorithm,
    SigningKeyBackend,
    SigningKeyPurpose,
    SigningKeyReference,
    SigningKeyStatus,
    SigningOperationRecord,
    SigningOperationStatus,
    TrustTier,
)


class SigningKeyNotFoundError(LookupError):
    pass


class SigningKeyStateError(RuntimeError):
    pass


class SigningConfigurationError(RuntimeError):
    pass


@dataclass(slots=True)
class SigningOutcome:
    payload_digest: str
    signature: str
    signing_operation: SigningOperationRecord


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class SigningService:
    def __init__(self, session: Session, *, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def register_key(
        self,
        *,
        tenant_id: str,
        display_name: str,
        key_purpose: SigningKeyPurpose,
        algorithm: SigningAlgorithm,
        key_backend: SigningKeyBackend,
        provider_key_ref: str | None,
        public_key_ref: str | None,
        issuer_name: str | None,
        issuer_uri: str | None,
        trust_tier: TrustTier | None,
        lifecycle_metadata: dict[str, Any],
        is_default: bool,
    ) -> SigningKeyReference:
        self._validate_backend_algorithm(key_backend=key_backend, algorithm=algorithm)

        active_existing_count = self.session.scalar(
            select(SigningKeyReference)
            .where(
                SigningKeyReference.tenant_id == tenant_id,
                SigningKeyReference.key_purpose == key_purpose,
                SigningKeyReference.status == SigningKeyStatus.active,
            )
            .limit(1)
        )

        key_reference = SigningKeyReference(
            signing_key_reference_id=uuid4().hex,
            tenant_id=tenant_id,
            display_name=display_name,
            issuer_name=issuer_name or self.settings.proof_issuer_name,
            issuer_uri=issuer_uri or self.settings.proof_issuer_uri,
            trust_tier=trust_tier or TrustTier(self.settings.proof_issuer_trust_tier),
            key_purpose=key_purpose,
            algorithm=algorithm,
            key_backend=key_backend,
            provider_key_ref=provider_key_ref or self._default_provider_key_ref(key_backend),
            public_key_ref=public_key_ref,
            status=SigningKeyStatus.active,
            is_default=is_default or active_existing_count is None,
            lifecycle_metadata=lifecycle_metadata,
            activated_at=utc_now(),
        )
        self.session.add(key_reference)

        if key_reference.is_default:
            self._unset_other_defaults(
                tenant_id=tenant_id,
                key_purpose=key_purpose,
                except_key_id=key_reference.signing_key_reference_id,
            )

        self.session.commit()
        self.session.refresh(key_reference)
        return key_reference

    def list_keys(
        self,
        *,
        tenant_id: str | None = None,
        key_purpose: SigningKeyPurpose | None = None,
        status: SigningKeyStatus | None = None,
    ) -> list[SigningKeyReference]:
        query = select(SigningKeyReference).order_by(SigningKeyReference.created_at.asc())
        if tenant_id is not None:
            query = query.where(SigningKeyReference.tenant_id == tenant_id)
        if key_purpose is not None:
            query = query.where(SigningKeyReference.key_purpose == key_purpose)
        if status is not None:
            query = query.where(SigningKeyReference.status == status)
        return list(self.session.scalars(query))

    def get_key(self, signing_key_reference_id: str) -> SigningKeyReference:
        key_reference = self.session.get(SigningKeyReference, signing_key_reference_id)
        if key_reference is None:
            raise SigningKeyNotFoundError(
                f"signing key reference '{signing_key_reference_id}' was not found"
            )
        return key_reference

    def activate_key(self, signing_key_reference_id: str) -> SigningKeyReference:
        key_reference = self.get_key(signing_key_reference_id)
        if key_reference.status in {SigningKeyStatus.revoked, SigningKeyStatus.retired}:
            raise SigningKeyStateError("revoked or retired keys may not be reactivated")

        key_reference.status = SigningKeyStatus.active
        key_reference.activated_at = utc_now()
        key_reference.suspended_at = None
        key_reference.is_default = True
        self.session.add(key_reference)
        self._unset_other_defaults(
            tenant_id=key_reference.tenant_id,
            key_purpose=key_reference.key_purpose,
            except_key_id=key_reference.signing_key_reference_id,
        )
        self.session.commit()
        self.session.refresh(key_reference)
        return key_reference

    def suspend_key(self, signing_key_reference_id: str) -> SigningKeyReference:
        key_reference = self.get_key(signing_key_reference_id)
        if key_reference.status == SigningKeyStatus.revoked:
            raise SigningKeyStateError("revoked keys may not be suspended")
        if key_reference.status == SigningKeyStatus.retired:
            raise SigningKeyStateError("retired keys may not be suspended")

        key_reference.status = SigningKeyStatus.suspended
        key_reference.suspended_at = utc_now()
        key_reference.is_default = False
        self.session.add(key_reference)
        self.session.commit()
        self.session.refresh(key_reference)
        return key_reference

    def resolve_key(
        self,
        *,
        tenant_id: str,
        key_purpose: SigningKeyPurpose,
        signing_key_reference_id: str | None,
    ) -> SigningKeyReference:
        if signing_key_reference_id is not None:
            key_reference = self.get_key(signing_key_reference_id)
        else:
            key_reference = self.session.scalar(
                select(SigningKeyReference).where(
                    SigningKeyReference.tenant_id == tenant_id,
                    SigningKeyReference.key_purpose == key_purpose,
                    SigningKeyReference.status == SigningKeyStatus.active,
                    SigningKeyReference.is_default.is_(True),
                )
            )
            if key_reference is None:
                key_reference = self.session.scalar(
                    select(SigningKeyReference).where(
                        SigningKeyReference.tenant_id == tenant_id,
                        SigningKeyReference.key_purpose == key_purpose,
                        SigningKeyReference.status == SigningKeyStatus.active,
                    )
                )

        if key_reference is None:
            raise SigningKeyNotFoundError(
                "no active signing key is available for the requested tenant and purpose"
            )
        if key_reference.status != SigningKeyStatus.active:
            raise SigningKeyStateError("signing key is not active")
        if key_reference.tenant_id != tenant_id:
            raise SigningKeyStateError("signing key does not belong to the requested tenant")
        return key_reference

    def sign_proof(
        self,
        *,
        issued_proof: IssuedProof,
        key_reference: SigningKeyReference,
        payload: dict[str, Any],
    ) -> SigningOutcome:
        if key_reference.status != SigningKeyStatus.active:
            raise SigningKeyStateError("signing key is not active")

        canonical_payload = canonical_json(payload)
        payload_digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        signing_operation = SigningOperationRecord(
            signing_operation_id=uuid4().hex,
            tenant_id=issued_proof.tenant_id,
            issued_proof_id=issued_proof.issued_proof_id,
            signing_key_reference_id=key_reference.signing_key_reference_id,
            algorithm=key_reference.algorithm,
            key_backend=key_reference.key_backend,
            status=SigningOperationStatus.requested,
            payload_digest=payload_digest,
        )
        self.session.add(signing_operation)
        self.session.flush()

        try:
            signature = self._sign_bytes(
                key_reference=key_reference,
                payload=canonical_payload.encode("utf-8"),
            )
        except Exception as exc:
            signing_operation.status = SigningOperationStatus.failed
            signing_operation.error_detail = str(exc)
            signing_operation.completed_at = utc_now()
            self.session.add(signing_operation)
            raise

        signing_operation.status = SigningOperationStatus.completed
        signing_operation.signature = signature
        signing_operation.provider_operation_ref = (
            f"{key_reference.key_backend.value}:{signing_operation.signing_operation_id}"
        )
        signing_operation.completed_at = utc_now()
        self.session.add(signing_operation)
        return SigningOutcome(
            payload_digest=payload_digest,
            signature=signature,
            signing_operation=signing_operation,
        )

    def _sign_bytes(
        self,
        *,
        key_reference: SigningKeyReference,
        payload: bytes,
    ) -> str:
        if key_reference.key_backend == SigningKeyBackend.development_local_hmac:
            if self.settings.environment == "production":
                raise SigningConfigurationError(
                    "development-local signing backend may not be used in production"
                )
            if key_reference.algorithm != SigningAlgorithm.hs256:
                raise SigningConfigurationError(
                    "development-local signing backend supports only HS256"
                )
            digest = hmac.new(
                self.settings.dev_signing_secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).digest()
            return self._base64url(digest)

        if key_reference.key_backend == SigningKeyBackend.external_managed:
            return self._sign_with_external_managed_backend(
                key_reference=key_reference,
                payload=payload,
            )

        raise SigningConfigurationError(
            f"unsupported signing backend '{key_reference.key_backend.value}'"
        )

    def _sign_with_external_managed_backend(
        self,
        *,
        key_reference: SigningKeyReference,
        payload: bytes,
    ) -> str:
        del payload
        raise SigningConfigurationError(
            "external_managed signing is configured for key "
            f"'{key_reference.signing_key_reference_id}' "
            f"(provider_key_ref='{key_reference.provider_key_ref}'), but the "
            "managed signing adapter is still a stub. Complete provider request "
            "signing, key resolution, timeout and retry policy, provider error "
            "mapping, and signature verification handling in app/services/signing.py "
            "before hosted use."
        )

    def _unset_other_defaults(
        self,
        *,
        tenant_id: str,
        key_purpose: SigningKeyPurpose,
        except_key_id: str,
    ) -> None:
        other_keys = list(
            self.session.scalars(
                select(SigningKeyReference).where(
                    SigningKeyReference.tenant_id == tenant_id,
                    SigningKeyReference.key_purpose == key_purpose,
                    SigningKeyReference.signing_key_reference_id != except_key_id,
                    SigningKeyReference.is_default.is_(True),
                )
            )
        )
        for other_key in other_keys:
            other_key.is_default = False
            self.session.add(other_key)

    def _validate_backend_algorithm(
        self,
        *,
        key_backend: SigningKeyBackend,
        algorithm: SigningAlgorithm,
    ) -> None:
        if (
            key_backend == SigningKeyBackend.development_local_hmac
            and algorithm != SigningAlgorithm.hs256
        ):
            raise SigningKeyStateError(
                "development-local signing keys must use HS256"
            )
        if (
            key_backend == SigningKeyBackend.external_managed
            and algorithm == SigningAlgorithm.hs256
        ):
            raise SigningKeyStateError(
                "external managed signing keys should use asymmetric algorithms"
            )

    def _default_provider_key_ref(self, key_backend: SigningKeyBackend) -> str:
        if key_backend == SigningKeyBackend.development_local_hmac:
            return "dev-local-hmac"
        return "external-managed-key"

    def _base64url(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")
