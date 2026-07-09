from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.escrow import EscrowRecord


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProofKind(enum.StrEnum):
    pccb = "pccb"


class ProofIssuanceStatus(enum.StrEnum):
    requested = "requested"
    issued = "issued"
    rejected = "rejected"
    failed = "failed"
    revoked = "revoked"
    expired = "expired"


class SigningKeyPurpose(enum.StrEnum):
    pccb_signing = "pccb_signing"
    approval_attestation_signing = "approval_attestation_signing"
    export_signing = "export_signing"


class SigningKeyStatus(enum.StrEnum):
    active = "active"
    suspended = "suspended"
    revoked = "revoked"
    retired = "retired"


class SigningKeyBackend(enum.StrEnum):
    development_local_hmac = "development_local_hmac"
    external_managed = "external_managed"


class SigningAlgorithm(enum.StrEnum):
    hs256 = "HS256"  # DEPRECATED — kept for migration compatibility, not for new keys
    rs256 = "RS256"
    es256 = "ES256"
    eddsa = "EdDSA"  # Ed25519 — the only supported algorithm for new keys


class SigningOperationStatus(enum.StrEnum):
    requested = "requested"
    completed = "completed"
    failed = "failed"


class TrustTier(enum.StrEnum):
    development_local = "development_local"
    tenant_managed = "tenant_managed"
    platform_managed = "platform_managed"


class SigningKeyReference(Base):
    __tablename__ = "signing_key_references"
    __table_args__ = (
        Index(
            "ix_signing_key_references_tenant_purpose_status",
            "tenant_id",
            "key_purpose",
            "status",
        ),
    )

    signing_key_reference_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    trust_tier: Mapped[TrustTier] = mapped_column(
        Enum(TrustTier, native_enum=False, validate_strings=True),
        nullable=False,
    )
    key_purpose: Mapped[SigningKeyPurpose] = mapped_column(
        Enum(SigningKeyPurpose, native_enum=False, validate_strings=True),
        nullable=False,
    )
    algorithm: Mapped[SigningAlgorithm] = mapped_column(
        Enum(SigningAlgorithm, native_enum=False, validate_strings=True),
        nullable=False,
    )
    key_backend: Mapped[SigningKeyBackend] = mapped_column(
        Enum(SigningKeyBackend, native_enum=False, validate_strings=True),
        nullable=False,
    )
    provider_key_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    public_key_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[SigningKeyStatus] = mapped_column(
        Enum(SigningKeyStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=SigningKeyStatus.active,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lifecycle_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    proofs: Mapped[list[IssuedProof]] = relationship(back_populates="signing_key")
    signing_operations: Mapped[list[SigningOperationRecord]] = relationship(
        back_populates="signing_key"
    )
    tenant = relationship("Tenant")


class IssuedProof(Base):
    __tablename__ = "issued_proofs"
    __table_args__ = (
        Index(
            "ix_issued_proofs_tenant_action_intent_created_at",
            "tenant_id",
            "action_intent_record_id",
            "created_at",
        ),
        Index("ix_issued_proofs_tenant_status", "tenant_id", "status"),
        Index(
            "uq_issued_proofs_active_idempotency",
            "tenant_id",
            "action_intent_record_id",
            "proof_kind",
            "audience",
            "scope_hash",
            "action_intent_digest",
            unique=True,
            sqlite_where=text("status IN ('requested', 'issued')"),
            postgresql_where=text("status IN ('requested', 'issued')"),
        ),
    )

    issued_proof_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    action_intent_record_id: Mapped[str] = mapped_column(
        ForeignKey("action_intent_records.action_intent_record_id"),
        nullable=False,
    )
    signing_key_reference_id: Mapped[str | None] = mapped_column(
        ForeignKey("signing_key_references.signing_key_reference_id"),
        nullable=True,
    )
    proof_kind: Mapped[ProofKind] = mapped_column(
        Enum(ProofKind, native_enum=False, validate_strings=True),
        nullable=False,
    )
    status: Mapped[ProofIssuanceStatus] = mapped_column(
        Enum(ProofIssuanceStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=ProofIssuanceStatus.requested,
    )
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    trust_tier: Mapped[TrustTier] = mapped_column(
        Enum(TrustTier, native_enum=False, validate_strings=True),
        nullable=False,
    )
    audience: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    scope_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    action_intent_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    proof_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    proof_payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm: Mapped[SigningAlgorithm | None] = mapped_column(
        Enum(SigningAlgorithm, native_enum=False, validate_strings=True),
        nullable=True,
    )
    issued_by_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_by_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    issuance_trace: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revocation_reason_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revocation_reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    revocation_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant")
    action_intent = relationship("ActionIntentRecord")
    signing_key: Mapped[SigningKeyReference | None] = relationship(back_populates="proofs")
    signing_operations: Mapped[list[SigningOperationRecord]] = relationship(
        back_populates="issued_proof"
    )
    escrow_record: Mapped[EscrowRecord | None] = relationship(
        "EscrowRecord",
        back_populates="issued_proof",
        uselist=False,
    )


class SigningOperationRecord(Base):
    __tablename__ = "signing_operation_records"
    __table_args__ = (
        Index(
            "ix_signing_operation_records_tenant_created_at",
            "tenant_id",
            "created_at",
        ),
    )

    signing_operation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    issued_proof_id: Mapped[str] = mapped_column(
        ForeignKey("issued_proofs.issued_proof_id"),
        nullable=False,
    )
    signing_key_reference_id: Mapped[str] = mapped_column(
        ForeignKey("signing_key_references.signing_key_reference_id"),
        nullable=False,
    )
    algorithm: Mapped[SigningAlgorithm] = mapped_column(
        Enum(SigningAlgorithm, native_enum=False, validate_strings=True),
        nullable=False,
    )
    key_backend: Mapped[SigningKeyBackend] = mapped_column(
        Enum(SigningKeyBackend, native_enum=False, validate_strings=True),
        nullable=False,
    )
    status: Mapped[SigningOperationStatus] = mapped_column(
        Enum(SigningOperationStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_operation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant")
    issued_proof: Mapped[IssuedProof] = relationship(back_populates="signing_operations")
    signing_key: Mapped[SigningKeyReference] = relationship(back_populates="signing_operations")
