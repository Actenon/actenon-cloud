from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class EscrowStatus(enum.StrEnum):
    held = "held"
    released = "released"
    consumed = "consumed"
    revoked = "revoked"
    quarantined = "quarantined"
    expired = "expired"


class ExecutionState(enum.StrEnum):
    not_requested = "not_requested"
    capability_held = "capability_held"
    capability_released = "capability_released"
    dispatch_requested = "dispatch_requested"
    dispatch_confirmed = "dispatch_confirmed"
    result_observed = "result_observed"
    failure_observed = "failure_observed"
    revoked = "revoked"
    quarantined = "quarantined"
    expired = "expired"


class CapabilityReleaseMode(enum.StrEnum):
    development_simulated = "development_simulated"
    external_managed = "external_managed"


class EscrowTransitionType(enum.StrEnum):
    hold_created = "hold_created"
    released = "released"
    consumed = "consumed"
    revoked = "revoked"
    quarantined = "quarantined"
    execution_update = "execution_update"
    expired = "expired"


class EscrowRecord(Base):
    __tablename__ = "escrow_records"
    __table_args__ = (
        UniqueConstraint("issued_proof_id", name="uq_escrow_records_issued_proof"),
        Index("ix_escrow_records_tenant_status", "tenant_id", "status"),
        Index(
            "ix_escrow_records_action_intent_execution_state",
            "action_intent_record_id",
            "execution_state",
        ),
    )

    escrow_record_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    action_intent_record_id: Mapped[str] = mapped_column(
        ForeignKey("action_intent_records.action_intent_record_id"),
        nullable=False,
    )
    issued_proof_id: Mapped[str] = mapped_column(
        ForeignKey("issued_proofs.issued_proof_id"),
        nullable=False,
    )
    capability_kind: Mapped[str] = mapped_column(String(255), nullable=False)
    protected_resource_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    release_mode: Mapped[CapabilityReleaseMode] = mapped_column(
        Enum(CapabilityReleaseMode, native_enum=False, validate_strings=True),
        nullable=False,
    )
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=EscrowStatus.held,
    )
    execution_state: Mapped[ExecutionState] = mapped_column(
        Enum(ExecutionState, native_enum=False, validate_strings=True),
        nullable=False,
        default=ExecutionState.capability_held,
    )
    audience: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    scope_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    action_intent_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    proof_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capability_token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capability_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    release_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    provider_execution_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revocation_reason_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revocation_reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    quarantine_reason_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quarantine_reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quarantined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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

    tenant = relationship("Tenant", back_populates="escrow_records")
    action_intent = relationship("ActionIntentRecord", back_populates="escrow_records")
    issued_proof = relationship("IssuedProof", back_populates="escrow_record")
    transitions: Mapped[list[EscrowTransitionRecord]] = relationship(
        back_populates="escrow_record",
        cascade="all, delete-orphan",
        order_by="EscrowTransitionRecord.created_at.asc()",
    )


class EscrowTransitionRecord(Base):
    __tablename__ = "escrow_transition_records"
    __table_args__ = (
        Index(
            "ix_escrow_transition_records_escrow_created_at",
            "escrow_record_id",
            "created_at",
        ),
        Index("ix_escrow_transition_records_tenant_created_at", "tenant_id", "created_at"),
    )

    escrow_transition_record_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    escrow_record_id: Mapped[str] = mapped_column(
        ForeignKey("escrow_records.escrow_record_id"),
        nullable=False,
    )
    transition_type: Mapped[EscrowTransitionType] = mapped_column(
        Enum(EscrowTransitionType, native_enum=False, validate_strings=True),
        nullable=False,
    )
    from_status: Mapped[EscrowStatus | None] = mapped_column(
        Enum(EscrowStatus, native_enum=False, validate_strings=True),
        nullable=True,
    )
    to_status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    from_execution_state: Mapped[ExecutionState | None] = mapped_column(
        Enum(ExecutionState, native_enum=False, validate_strings=True),
        nullable=True,
    )
    to_execution_state: Mapped[ExecutionState] = mapped_column(
        Enum(ExecutionState, native_enum=False, validate_strings=True),
        nullable=False,
    )
    actor_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    transition_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="escrow_transitions")
    escrow_record: Mapped[EscrowRecord] = relationship(back_populates="transitions")
