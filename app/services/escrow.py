from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.models import (
    ActionIntentRecord,
    CapabilityReleaseMode,
    EscrowRecord,
    EscrowStatus,
    EscrowTransitionRecord,
    EscrowTransitionType,
    ExecutionState,
    IssuedProof,
    ProofIssuanceStatus,
)
from app.services.kernel_bridge import resolve_signer


class EscrowRecordNotFoundError(LookupError):
    pass


class EscrowStateError(RuntimeError):
    pass


class EscrowValidationError(ValueError):
    pass


class CapabilityReleaseNotAvailableError(NotImplementedError):
    pass


class CapabilityTokenValidationError(PermissionError):
    pass


@dataclass(slots=True)
class EscrowActor:
    principal_type: str
    principal_id: str


@dataclass(slots=True)
class EscrowCreateResult:
    record: EscrowRecord
    idempotent_replay: bool


@dataclass(slots=True)
class EscrowReleaseResult:
    record: EscrowRecord
    capability_token: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _b64url_encode(raw: bytes) -> str:
    """Encode bytes as unpadded URL-safe base64 (JWT-style)."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign_capability_token(
    *,
    signer: Any,
    escrow_id: str,
    action_intent_digest: str,
    scope: list[str],
    audience: str,
    expiry: datetime,
    nonce: str,
) -> tuple[str, str, str]:
    """Mint a signed JWT-like capability token bound to an escrow record.

    The token has three base64url segments separated by ``.``:

      header.payload.signature

    where ``header`` carries the signing algorithm and key id, ``payload``
    carries the bounded capability claims (escrow_id, action_intent_digest,
    scope, audience, expiry, nonce), and ``signature`` is the signer's
    EdDSA / HMAC signature over the ``header.payload`` signing input.

    Returns ``(capability_token, key_id, algorithm)`` so callers can record
    provenance in the release metadata.
    """
    header = {
        "alg": signer.algorithm,
        "typ": "acp-cap+jwt",
        "kid": signer.key_id,
    }
    payload = {
        "escrow_id": escrow_id,
        "action_intent_digest": action_intent_digest,
        "scope": list(scope),
        "audience": audience,
        "exp": int(normalize_utc(expiry).timestamp()),
        "nonce": nonce,
    }
    header_part = _b64url_encode(
        json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    payload_part = _b64url_encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_part}.{payload_part}".encode()
    signature_spec = signer.sign(signing_input)
    signature_part = signature_spec.value
    capability_token = f"{header_part}.{payload_part}.{signature_part}"
    return capability_token, signature_spec.key_id, signature_spec.algorithm


def verify_capability_token(capability_token: str, *, signer: Any) -> dict[str, Any]:
    """Verify a signed JWT-like capability token and return its payload.

    Raises ``CapabilityTokenValidationError`` if the token is malformed or
    the signature does not verify against ``signer``.
    """
    parts = capability_token.split(".")
    if len(parts) != 3:
        raise CapabilityTokenValidationError("capability token must have three segments")
    header_part, payload_part, signature_part = parts
    try:
        header = json.loads(_b64url_decode(header_part).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CapabilityTokenValidationError(
            "capability token header or payload is invalid"
        ) from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise CapabilityTokenValidationError("capability token segments must be JSON objects")
    if header.get("typ") != "acp-cap+jwt":
        raise CapabilityTokenValidationError(
            "capability token header is not an acp-cap+jwt token"
        )
    signing_input = f"{header_part}.{payload_part}".encode()
    from actenon.proof.signers.external_managed import SignatureSpec

    signature_spec = SignatureSpec(
        algorithm=header.get("alg", ""),
        key_id=header.get("kid", ""),
        encoding="base64url",
        value=signature_part,
    )
    if not signer.verify(signing_input, signature_spec):
        raise CapabilityTokenValidationError(
            "capability token signature is invalid for the configured signer"
        )
    return payload


class EscrowService:
    def __init__(self, session: Session, *, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def create_hold(
        self,
        *,
        issued_proof_id: str,
        capability_kind: str,
        protected_resource_ref: str,
        requested_by: EscrowActor,
        expires_in_seconds: int | None,
        capability_metadata: dict[str, Any],
    ) -> EscrowCreateResult:
        proof = self._get_proof(issued_proof_id)
        self._ensure_active_issued_proof(proof)

        capability_kind_normalized = capability_kind.strip()
        protected_resource_ref_normalized = protected_resource_ref.strip()
        if not capability_kind_normalized:
            raise EscrowValidationError("capability_kind must not be empty")
        if not protected_resource_ref_normalized:
            raise EscrowValidationError("protected_resource_ref must not be empty")

        existing = self.session.scalar(
            self._record_query().where(EscrowRecord.issued_proof_id == issued_proof_id)
        )
        if existing is not None:
            if self._refresh_if_expired(existing):
                self.session.commit()
                existing = self.get_record(existing.escrow_record_id)

            if (
                existing.capability_kind != capability_kind_normalized
                or existing.protected_resource_ref != protected_resource_ref_normalized
            ):
                raise EscrowStateError(
                    "issued proof is already bound to a different escrow capability record"
                )
            return EscrowCreateResult(record=existing, idempotent_replay=True)

        release_mode = CapabilityReleaseMode(self.settings.capability_release_mode)
        record = EscrowRecord(
            escrow_record_id=uuid4().hex,
            tenant_id=proof.tenant_id,
            action_intent_record_id=proof.action_intent_record_id,
            issued_proof_id=proof.issued_proof_id,
            capability_kind=capability_kind_normalized,
            protected_resource_ref=protected_resource_ref_normalized,
            release_mode=release_mode,
            status=EscrowStatus.held,
            execution_state=ExecutionState.capability_held,
            audience=proof.audience,
            scope=list(proof.scope),
            scope_hash=proof.scope_hash,
            action_intent_digest=proof.action_intent_digest,
            proof_nonce=proof.nonce,
            created_by_principal_type=requested_by.principal_type,
            created_by_principal_id=requested_by.principal_id,
            capability_metadata=capability_metadata,
            release_metadata={},
            expires_at=self._resolve_expires_at(
                proof=proof,
                expires_in_seconds=expires_in_seconds,
            ),
        )
        self.session.add(record)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            existing = self.session.scalar(
                self._record_query().where(EscrowRecord.issued_proof_id == issued_proof_id)
            )
            if existing is not None:
                if (
                    existing.capability_kind != capability_kind_normalized
                    or existing.protected_resource_ref != protected_resource_ref_normalized
                ):
                    raise EscrowStateError(
                        "issued proof is already bound to a different escrow capability record"
                    ) from exc
                return EscrowCreateResult(record=existing, idempotent_replay=True)
            raise
        self._append_transition(
            record=record,
            transition_type=EscrowTransitionType.hold_created,
            actor=requested_by,
            from_status=None,
            to_status=record.status,
            from_execution_state=None,
            to_execution_state=record.execution_state,
            transition_metadata={
                "issued_proof_id": proof.issued_proof_id,
                "release_mode": release_mode.value,
                "simulated": release_mode == CapabilityReleaseMode.development_simulated,
            },
        )
        self._synchronize_action_intent_execution_state(record.action_intent_record_id)
        self.session.commit()
        return EscrowCreateResult(
            record=self.get_record(record.escrow_record_id),
            idempotent_replay=False,
        )

    def release_capability(
        self,
        escrow_record_id: str,
        *,
        released_by: EscrowActor,
    ) -> EscrowReleaseResult:
        record = self.get_record(escrow_record_id)
        self._ensure_active_issued_proof(record.issued_proof)

        if record.status != EscrowStatus.held:
            raise EscrowStateError(
                "capability release is only allowed from held escrow state"
            )

        if record.release_mode == CapabilityReleaseMode.external_managed:
            raise CapabilityReleaseNotAvailableError(
                "external managed capability release is modeled but not implemented"
            )

        # B4: real permit-broker release. The capability token is now a signed
        # JWT-like structure (Ed25519 when a key is configured, dev-HMAC only
        # as the pilot fallback) bound to the escrow's action_intent_digest,
        # scope, audience, expiry, and a fresh nonce. This replaces the prior
        # ``secrets.token_urlsafe(32)`` simulation.
        capability_nonce = uuid4().hex
        capability_expiry = (
            record.expires_at
            if record.expires_at is not None
            else utc_now() + timedelta(seconds=self.settings.capability_default_ttl_seconds)
        )
        signer = resolve_signer()
        capability_token, capability_key_id, capability_algorithm = _sign_capability_token(
            signer=signer,
            escrow_id=record.escrow_record_id,
            action_intent_digest=record.action_intent_digest,
            scope=list(record.scope),
            audience=record.audience,
            expiry=capability_expiry,
            nonce=capability_nonce,
        )
        now = utc_now()
        previous_status = record.status
        previous_execution_state = record.execution_state
        capability_reference = f"cap_{uuid4().hex}"
        capability_token_digest = self._token_digest(capability_token)
        release_metadata = {
            **record.release_metadata,
            "simulated": False,
            "release_mode": record.release_mode.value,
            "provider_integration": "permit_broker_signed_capability",
            "signing": {
                "algorithm": capability_algorithm,
                "key_id": capability_key_id,
                "typ": "acp-cap+jwt",
                "nonce": capability_nonce,
            },
            "binding": {
                "audience": record.audience,
                "scope": list(record.scope),
                "scope_hash": record.scope_hash,
                "action_intent_digest": record.action_intent_digest,
                "proof_nonce": record.proof_nonce,
                "expiry": normalize_utc(capability_expiry).isoformat(),
            },
        }
        release_claim = self.session.execute(
            update(EscrowRecord)
            .where(
                EscrowRecord.escrow_record_id == escrow_record_id,
                EscrowRecord.status == EscrowStatus.held,
            )
            .values(
                status=EscrowStatus.released,
                execution_state=ExecutionState.capability_released,
                capability_reference=capability_reference,
                capability_token_digest=capability_token_digest,
                release_metadata=release_metadata,
                released_at=now,
                updated_at=now,
            )
        )
        if release_claim.rowcount != 1:
            self.session.rollback()
            raise EscrowStateError(
                "capability release is only allowed from held escrow state"
            )
        self.session.expire(record)
        self.session.refresh(record)
        self._append_transition(
            record=record,
            transition_type=EscrowTransitionType.released,
            actor=released_by,
            from_status=previous_status,
            to_status=record.status,
            from_execution_state=previous_execution_state,
            to_execution_state=record.execution_state,
            transition_metadata={
                "simulated": False,
                "capability_reference": capability_reference,
                "signing_algorithm": capability_algorithm,
                "signing_key_id": capability_key_id,
            },
        )
        self._synchronize_action_intent_execution_state(record.action_intent_record_id)
        self.session.commit()
        return EscrowReleaseResult(
            record=self.get_record(record.escrow_record_id),
            capability_token=capability_token,
        )

    def consume_capability(
        self,
        escrow_record_id: str,
        *,
        capability_token: str,
        consumed_by: EscrowActor,
        provider_execution_ref: str | None,
        provider_status: str | None,
        transition_metadata: dict[str, Any],
    ) -> EscrowRecord:
        record = self.get_record(escrow_record_id)
        self._ensure_active_issued_proof(record.issued_proof)

        if record.status != EscrowStatus.released:
            raise EscrowStateError(
                "capability consumption is only allowed from released escrow state"
            )
        if not record.capability_token_digest:
            raise EscrowStateError("released capability is missing a token digest")
        capability_token_digest = self._token_digest(capability_token)
        if capability_token_digest != record.capability_token_digest:
            raise CapabilityTokenValidationError("capability token is invalid for this escrow")

        previous_status = record.status
        previous_execution_state = record.execution_state
        now = utc_now()
        consume_claim = self.session.execute(
            update(EscrowRecord)
            .where(
                EscrowRecord.escrow_record_id == escrow_record_id,
                EscrowRecord.status == EscrowStatus.released,
                EscrowRecord.capability_token_digest == capability_token_digest,
            )
            .values(
                status=EscrowStatus.consumed,
                execution_state=ExecutionState.dispatch_requested,
                consumed_at=now,
                provider_execution_ref=provider_execution_ref or record.provider_execution_ref,
                provider_status=provider_status or record.provider_status,
                updated_at=now,
            )
        )
        if consume_claim.rowcount != 1:
            self.session.rollback()
            raise EscrowStateError(
                "capability consumption is only allowed from released escrow state"
            )
        self.session.expire(record)
        self.session.refresh(record)
        self._append_transition(
            record=record,
            transition_type=EscrowTransitionType.consumed,
            actor=consumed_by,
            from_status=previous_status,
            to_status=record.status,
            from_execution_state=previous_execution_state,
            to_execution_state=record.execution_state,
            transition_metadata={
                **transition_metadata,
                "provider_execution_ref": provider_execution_ref,
                "provider_status": provider_status,
            },
        )
        self._synchronize_action_intent_execution_state(record.action_intent_record_id)
        self.session.commit()
        return self.get_record(record.escrow_record_id)

    def revoke_capability(
        self,
        escrow_record_id: str,
        *,
        acted_by: EscrowActor,
        reason_code: str,
        reason_detail: str | None,
        transition_metadata: dict[str, Any],
    ) -> EscrowRecord:
        record = self.get_record(escrow_record_id)

        if record.status not in {EscrowStatus.held, EscrowStatus.released}:
            raise EscrowStateError(
                "only held or released capabilities can be revoked; consumed capabilities "
                "must be quarantined instead"
            )

        previous_status = record.status
        previous_execution_state = record.execution_state
        record.status = EscrowStatus.revoked
        record.execution_state = ExecutionState.revoked
        record.revocation_reason_code = reason_code
        record.revocation_reason_detail = reason_detail
        record.revoked_at = utc_now()
        self.session.add(record)
        self._append_transition(
            record=record,
            transition_type=EscrowTransitionType.revoked,
            actor=acted_by,
            from_status=previous_status,
            to_status=record.status,
            from_execution_state=previous_execution_state,
            to_execution_state=record.execution_state,
            reason_code=reason_code,
            reason_detail=reason_detail,
            transition_metadata=transition_metadata,
        )
        self._synchronize_action_intent_execution_state(record.action_intent_record_id)
        self.session.commit()
        return self.get_record(record.escrow_record_id)

    def quarantine_capability(
        self,
        escrow_record_id: str,
        *,
        acted_by: EscrowActor,
        reason_code: str,
        reason_detail: str | None,
        transition_metadata: dict[str, Any],
    ) -> EscrowRecord:
        record = self.get_record(escrow_record_id)

        if record.status in {
            EscrowStatus.revoked,
            EscrowStatus.quarantined,
            EscrowStatus.expired,
        }:
            raise EscrowStateError(
                f"capability cannot be quarantined from status={record.status.value}"
            )

        previous_status = record.status
        previous_execution_state = record.execution_state
        record.status = EscrowStatus.quarantined
        record.execution_state = ExecutionState.quarantined
        record.quarantine_reason_code = reason_code
        record.quarantine_reason_detail = reason_detail
        record.quarantined_at = utc_now()
        self.session.add(record)
        self._append_transition(
            record=record,
            transition_type=EscrowTransitionType.quarantined,
            actor=acted_by,
            from_status=previous_status,
            to_status=record.status,
            from_execution_state=previous_execution_state,
            to_execution_state=record.execution_state,
            reason_code=reason_code,
            reason_detail=reason_detail,
            transition_metadata=transition_metadata,
        )
        self._synchronize_action_intent_execution_state(record.action_intent_record_id)
        self.session.commit()
        return self.get_record(record.escrow_record_id)

    def record_execution_update(
        self,
        escrow_record_id: str,
        *,
        observed_by: EscrowActor,
        execution_state: ExecutionState,
        provider_execution_ref: str | None,
        provider_status: str | None,
        transition_metadata: dict[str, Any],
    ) -> EscrowRecord:
        record = self.get_record(escrow_record_id)

        if record.status != EscrowStatus.consumed:
            raise EscrowStateError(
                "execution updates require a consumed capability escrow record"
            )
        if execution_state not in {
            ExecutionState.dispatch_confirmed,
            ExecutionState.result_observed,
            ExecutionState.failure_observed,
        }:
            raise EscrowValidationError(
                "execution updates may only report dispatch_confirmed, "
                "result_observed, or failure_observed"
            )
        if not self._is_allowed_execution_progression(
            current_state=record.execution_state,
            new_state=execution_state,
        ):
            raise EscrowStateError(
                f"invalid execution state transition from {record.execution_state.value} "
                f"to {execution_state.value}"
            )

        previous_execution_state = record.execution_state
        record.execution_state = execution_state
        if provider_execution_ref:
            record.provider_execution_ref = provider_execution_ref
        if provider_status:
            record.provider_status = provider_status
        self.session.add(record)
        self._append_transition(
            record=record,
            transition_type=EscrowTransitionType.execution_update,
            actor=observed_by,
            from_status=record.status,
            to_status=record.status,
            from_execution_state=previous_execution_state,
            to_execution_state=record.execution_state,
            transition_metadata={
                **transition_metadata,
                "provider_execution_ref": provider_execution_ref,
                "provider_status": provider_status,
            },
        )
        self._synchronize_action_intent_execution_state(record.action_intent_record_id)
        self.session.commit()
        return self.get_record(record.escrow_record_id)

    def list_records(
        self,
        *,
        tenant_id: str | None = None,
        action_intent_record_id: str | None = None,
        issued_proof_id: str | None = None,
        status: EscrowStatus | None = None,
        execution_state: ExecutionState | None = None,
    ) -> list[EscrowRecord]:
        query = self._record_query().order_by(EscrowRecord.created_at.asc())
        if tenant_id is not None:
            query = query.where(EscrowRecord.tenant_id == tenant_id)
        if action_intent_record_id is not None:
            query = query.where(EscrowRecord.action_intent_record_id == action_intent_record_id)
        if issued_proof_id is not None:
            query = query.where(EscrowRecord.issued_proof_id == issued_proof_id)
        if status is not None:
            query = query.where(EscrowRecord.status == status)
        if execution_state is not None:
            query = query.where(EscrowRecord.execution_state == execution_state)

        records = list(self.session.scalars(query))
        changed = False
        for record in records:
            if self._refresh_if_expired(record):
                changed = True
        if changed:
            self.session.commit()
            records = list(self.session.scalars(query))
        return records

    def get_record(self, escrow_record_id: str) -> EscrowRecord:
        self.session.expire_all()
        record = self.session.scalar(
            self._record_query().where(EscrowRecord.escrow_record_id == escrow_record_id)
        )
        if record is None:
            raise EscrowRecordNotFoundError(
                f"escrow record '{escrow_record_id}' was not found"
            )

        if self._refresh_if_expired(record):
            self.session.commit()
            record = self.session.scalar(
                self._record_query().where(EscrowRecord.escrow_record_id == escrow_record_id)
            )
            if record is None:
                raise RuntimeError("escrow record disappeared during status refresh")
        return record

    def _record_query(self):
        return select(EscrowRecord).options(
            selectinload(EscrowRecord.transitions),
            selectinload(EscrowRecord.issued_proof),
        )

    def _get_proof(self, issued_proof_id: str) -> IssuedProof:
        proof = self.session.get(IssuedProof, issued_proof_id)
        if proof is None:
            raise EscrowValidationError(f"issued proof '{issued_proof_id}' was not found")
        return proof

    def _ensure_active_issued_proof(self, proof: IssuedProof) -> None:
        self._refresh_proof_if_expired(proof)
        if proof.status != ProofIssuanceStatus.issued:
            raise EscrowValidationError(
                "capability escrow requires an issued, non-expired, non-revoked proof"
            )

    def _refresh_proof_if_expired(self, proof: IssuedProof) -> bool:
        if proof.status != ProofIssuanceStatus.issued:
            return False
        if normalize_utc(proof.expires_at) > utc_now():
            return False
        proof.status = ProofIssuanceStatus.expired
        self.session.add(proof)
        return True

    def _refresh_if_expired(self, record: EscrowRecord) -> bool:
        if record.status not in {EscrowStatus.held, EscrowStatus.released}:
            return False
        if normalize_utc(record.expires_at) > utc_now():
            return False

        previous_status = record.status
        previous_execution_state = record.execution_state
        record.status = EscrowStatus.expired
        record.execution_state = ExecutionState.expired
        record.failure_reason = "capability escrow expired before execution completed"
        self.session.add(record)
        self._append_transition(
            record=record,
            transition_type=EscrowTransitionType.expired,
            actor=EscrowActor(principal_type="system", principal_id="escrow-expiry"),
            from_status=previous_status,
            to_status=record.status,
            from_execution_state=previous_execution_state,
            to_execution_state=record.execution_state,
            transition_metadata={},
        )
        self._synchronize_action_intent_execution_state(record.action_intent_record_id)
        return True

    def _resolve_expires_at(
        self,
        *,
        proof: IssuedProof,
        expires_in_seconds: int | None,
    ) -> datetime:
        requested_ttl = expires_in_seconds or self.settings.capability_default_ttl_seconds
        if requested_ttl > self.settings.capability_max_ttl_seconds:
            raise EscrowValidationError(
                "requested capability expiry exceeds the configured maximum TTL"
            )

        requested_expiry = utc_now() + timedelta(seconds=requested_ttl)
        proof_expiry = normalize_utc(proof.expires_at)
        return min(requested_expiry, proof_expiry)

    def _append_transition(
        self,
        *,
        record: EscrowRecord,
        transition_type: EscrowTransitionType,
        actor: EscrowActor,
        from_status: EscrowStatus | None,
        to_status: EscrowStatus,
        from_execution_state: ExecutionState | None,
        to_execution_state: ExecutionState,
        reason_code: str | None = None,
        reason_detail: str | None = None,
        transition_metadata: dict[str, Any],
    ) -> None:
        transition = EscrowTransitionRecord(
            escrow_transition_record_id=uuid4().hex,
            tenant_id=record.tenant_id,
            escrow_record_id=record.escrow_record_id,
            transition_type=transition_type,
            from_status=from_status,
            to_status=to_status,
            from_execution_state=from_execution_state,
            to_execution_state=to_execution_state,
            actor_principal_type=actor.principal_type,
            actor_principal_id=actor.principal_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            transition_metadata=transition_metadata,
        )
        self.session.add(transition)

    def _synchronize_action_intent_execution_state(self, action_intent_record_id: str) -> None:
        record = self.session.get(ActionIntentRecord, action_intent_record_id)
        if record is None:
            raise RuntimeError("linked Action Intent disappeared during escrow state sync")

        latest_escrow = self.session.scalar(
            select(EscrowRecord)
            .where(EscrowRecord.action_intent_record_id == action_intent_record_id)
            .order_by(EscrowRecord.updated_at.desc(), EscrowRecord.created_at.desc())
        )
        record.execution_state = (
            latest_escrow.execution_state
            if latest_escrow is not None
            else ExecutionState.not_requested
        )
        self.session.add(record)

    def _is_allowed_execution_progression(
        self,
        *,
        current_state: ExecutionState,
        new_state: ExecutionState,
    ) -> bool:
        allowed = {
            ExecutionState.dispatch_requested: {
                ExecutionState.dispatch_confirmed,
                ExecutionState.result_observed,
                ExecutionState.failure_observed,
            },
            ExecutionState.dispatch_confirmed: {
                ExecutionState.result_observed,
                ExecutionState.failure_observed,
            },
            ExecutionState.result_observed: set(),
            ExecutionState.failure_observed: set(),
        }
        return new_state in allowed.get(current_state, set())

    def _token_digest(self, capability_token: str) -> str:
        normalized_token = capability_token.strip()
        if not normalized_token:
            raise CapabilityTokenValidationError("capability token must not be empty")
        return sha256(normalized_token.encode("utf-8")).hexdigest()
