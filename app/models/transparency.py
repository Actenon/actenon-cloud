from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class TransparencyCheckpointStatus(enum.StrEnum):
    requested = "requested"
    completed = "completed"
    failed = "failed"


class TransparencyLogState(Base):
    __tablename__ = "transparency_log_states"

    log_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    log_identity: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    next_leaf_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    append_chain_head: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_checkpoint_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_checkpoint_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
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


class TransparencyLogLeaf(Base):
    __tablename__ = "transparency_log_leaves"
    __table_args__ = (
        UniqueConstraint("log_id", "leaf_index", name="uq_transparency_leaf_index"),
        UniqueConstraint("log_id", "receipt_digest", name="uq_transparency_receipt_digest"),
        Index("ix_transparency_leaves_log_index", "log_id", "leaf_index"),
    )

    leaf_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    log_id: Mapped[str] = mapped_column(String(512), nullable=False)
    leaf_index: Mapped[int] = mapped_column(Integer, nullable=False)
    receipt_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    leaf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    append_chain_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class TransparencyCheckpointRecord(Base):
    __tablename__ = "transparency_checkpoint_records"
    __table_args__ = (
        UniqueConstraint(
            "log_id",
            "tree_size",
            name="uq_transparency_checkpoint_tree_size",
        ),
        Index(
            "ix_transparency_checkpoints_log_size",
            "log_id",
            "tree_size",
        ),
        Index(
            "ix_transparency_checkpoints_status_created",
            "status",
            "created_at",
        ),
    )

    checkpoint_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    log_id: Mapped[str] = mapped_column(String(512), nullable=False)
    tree_size: Mapped[int] = mapped_column(Integer, nullable=False)
    root_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    key_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[TransparencyCheckpointStatus] = mapped_column(
        Enum(TransparencyCheckpointStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    signing_input_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkpoint_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prior_checkpoint_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_operation_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    checkpoint_artifact: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    actor_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class TransparencyIntegrityEvent(Base):
    __tablename__ = "transparency_integrity_events"
    __table_args__ = (
        Index(
            "ix_transparency_integrity_log_detected",
            "log_id",
            "detected_at",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    log_id: Mapped[str] = mapped_column(String(512), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


__all__ = [
    "TransparencyCheckpointRecord",
    "TransparencyCheckpointStatus",
    "TransparencyIntegrityEvent",
    "TransparencyLogLeaf",
    "TransparencyLogState",
]
