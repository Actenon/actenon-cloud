from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReceiptState(enum.StrEnum):
    none = "none"
    received = "received"
    indexed = "indexed"
    reconciled = "reconciled"
    superseded = "superseded"


class ReconciliationType(enum.StrEnum):
    intent_to_receipt = "intent_to_receipt"
    proof_to_receipt = "proof_to_receipt"
    escrow_to_receipt = "escrow_to_receipt"


class ReconciliationStatus(enum.StrEnum):
    matched = "matched"
    manual_review_required = "manual_review_required"
    mismatch = "mismatch"


class ReceiptRecord(Base):
    __tablename__ = "receipt_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "kernel_receipt_digest",
            name="uq_receipt_records_tenant_digest",
        ),
        Index(
            "ix_receipt_records_tenant_action_intent_timestamp",
            "tenant_id",
            "action_intent_record_id",
            "receipt_timestamp",
        ),
        Index("ix_receipt_records_tenant_type_outcome", "tenant_id", "receipt_type", "outcome"),
        Index("ix_receipt_records_provider_execution_ref", "provider_execution_ref"),
    )

    receipt_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    action_intent_record_id: Mapped[str] = mapped_column(
        ForeignKey("action_intent_records.action_intent_record_id"),
        nullable=False,
    )
    issued_proof_id: Mapped[str | None] = mapped_column(
        ForeignKey("issued_proofs.issued_proof_id"),
        nullable=True,
    )
    escrow_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("escrow_records.escrow_record_id"),
        nullable=True,
    )
    contract_family: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_validation_errors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    external_receipt_id: Mapped[str] = mapped_column(String(255), nullable=False)
    receipt_type: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kernel_receipt_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    receipt_index: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    linked_approval_request_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    linked_approval_decision_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    linked_evidence_object_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    provider_execution_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settlement_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_by_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    received_by_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    receipt_state: Mapped[ReceiptState] = mapped_column(
        Enum(ReceiptState, native_enum=False, validate_strings=True),
        nullable=False,
        default=ReceiptState.received,
    )
    reconciliation_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
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

    tenant = relationship("Tenant", back_populates="receipt_records")
    action_intent = relationship("ActionIntentRecord", back_populates="receipt_records")
    issued_proof = relationship("IssuedProof")
    escrow_record = relationship("EscrowRecord")
    reconciliation_records: Mapped[list[ReconciliationRecord]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="receipt")


class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"
    __table_args__ = (
        Index(
            "ix_reconciliation_records_action_intent_created_at",
            "action_intent_record_id",
            "created_at",
        ),
        Index(
            "ix_reconciliation_records_tenant_type_status",
            "tenant_id",
            "reconciliation_type",
            "status",
        ),
    )

    reconciliation_record_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    action_intent_record_id: Mapped[str] = mapped_column(
        ForeignKey("action_intent_records.action_intent_record_id"),
        nullable=False,
    )
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("receipt_records.receipt_id"),
        nullable=False,
    )
    issued_proof_id: Mapped[str | None] = mapped_column(
        ForeignKey("issued_proofs.issued_proof_id"),
        nullable=True,
    )
    escrow_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("escrow_records.escrow_record_id"),
        nullable=True,
    )
    reconciliation_type: Mapped[ReconciliationType] = mapped_column(
        Enum(ReconciliationType, native_enum=False, validate_strings=True),
        nullable=False,
    )
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    hook_name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
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

    tenant = relationship("Tenant", back_populates="reconciliation_records")
    action_intent = relationship("ActionIntentRecord", back_populates="reconciliation_records")
    receipt: Mapped[ReceiptRecord] = relationship(back_populates="reconciliation_records")
    issued_proof = relationship("IssuedProof")
    escrow_record = relationship("EscrowRecord")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_tenant_created_at", "tenant_id", "created_at"),
        Index(
            "ix_audit_events_action_intent_event_type",
            "action_intent_record_id",
            "event_type",
        ),
        Index("ix_audit_events_subject", "subject_type", "subject_id"),
    )

    audit_event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    action_intent_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("action_intent_records.action_intent_record_id"),
        nullable=True,
    )
    receipt_id: Mapped[str | None] = mapped_column(
        ForeignKey("receipt_records.receipt_id"),
        nullable=True,
    )
    issued_proof_id: Mapped[str | None] = mapped_column(
        ForeignKey("issued_proofs.issued_proof_id"),
        nullable=True,
    )
    escrow_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("escrow_records.escrow_record_id"),
        nullable=True,
    )
    event_category: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="audit_events")
    action_intent = relationship("ActionIntentRecord", back_populates="audit_events")
    receipt: Mapped[ReceiptRecord | None] = relationship(back_populates="audit_events")
    issued_proof = relationship("IssuedProof")
    escrow_record = relationship("EscrowRecord")
