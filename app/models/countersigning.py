from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class CounterSigningKeyStatus(enum.StrEnum):
    active = "active"
    retired = "retired"
    revoked = "revoked"


class CounterSigningOperationStatus(enum.StrEnum):
    requested = "requested"
    completed = "completed"
    denied = "denied"
    failed = "failed"


class CounterSigningLifecycleAction(enum.StrEnum):
    provision = "provision"
    rotate = "rotate"
    revoke = "revoke"


class CounterSigningLifecycleStatus(enum.StrEnum):
    requested = "requested"
    completed = "completed"
    denied = "denied"
    failed = "failed"


class CounterSigningKey(Base):
    __tablename__ = "counter_signing_keys"
    __table_args__ = (Index("ix_counter_signing_keys_status_created_at", "status", "created_at"),)

    key_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    provider_key_ref: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    public_key_jwk: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    witness: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    origin: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[CounterSigningKeyStatus] = mapped_column(
        Enum(CounterSigningKeyStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_key_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    provider_attestation_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    lifecycle_metadata: Mapped[dict[str, Any]] = mapped_column(
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


class CounterSigningOperationRecord(Base):
    __tablename__ = "counter_signing_operation_records"
    __table_args__ = (
        Index(
            "ix_counter_signing_operations_status_created_at",
            "status",
            "created_at",
        ),
        Index(
            "ix_counter_signing_operations_receipt_digest",
            "receipt_digest",
        ),
        Index(
            "ix_counter_signing_operations_actor",
            "actor_principal_type",
            "actor_principal_id",
        ),
    )

    operation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    receipt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    signing_input_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    key_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    actor_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CounterSigningOperationStatus] = mapped_column(
        Enum(CounterSigningOperationStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    provider_operation_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    countersignature_artifact: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
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


class CounterSigningLifecycleRecord(Base):
    __tablename__ = "counter_signing_lifecycle_records"
    __table_args__ = (
        Index(
            "ix_counter_signing_lifecycle_action_created_at",
            "action",
            "created_at",
        ),
        Index(
            "ix_counter_signing_lifecycle_target_key",
            "target_key_id",
        ),
    )

    lifecycle_operation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    action: Mapped[CounterSigningLifecycleAction] = mapped_column(
        Enum(CounterSigningLifecycleAction, native_enum=False, validate_strings=True),
        nullable=False,
    )
    status: Mapped[CounterSigningLifecycleStatus] = mapped_column(
        Enum(CounterSigningLifecycleStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    target_key_id: Mapped[str] = mapped_column(String(256), nullable=False)
    prior_key_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    requester_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    requester_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_principal_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    provider_operation_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    published_key_set_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
