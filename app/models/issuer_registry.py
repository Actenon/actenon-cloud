from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class IssuerStanding(enum.StrEnum):
    good_standing = "good_standing"
    suspended = "suspended"
    revoked = "revoked"


class IssuerStatusPublicationStatus(enum.StrEnum):
    requested = "requested"
    completed = "completed"
    failed = "failed"


class IssuerRegistryRecord(Base):
    __tablename__ = "issuer_registry_records"
    __table_args__ = (
        UniqueConstraint(
            "issuer_type",
            "issuer_id",
            name="uq_issuer_registry_identity",
        ),
        Index(
            "ix_issuer_registry_standing_updated",
            "standing",
            "updated_at",
        ),
    )

    registry_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    issuer_type: Mapped[str] = mapped_column(String(64), nullable=False)
    issuer_id: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    standing: Mapped[IssuerStanding] = mapped_column(
        Enum(IssuerStanding, native_enum=False, validate_strings=True),
        nullable=False,
    )
    standing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    registry_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    standing_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    def identity(self) -> dict[str, str]:
        identity = {"type": self.issuer_type, "id": self.issuer_id}
        if self.display_name is not None:
            identity["display_name"] = self.display_name
        return identity


class IssuerStatusPublicationRecord(Base):
    __tablename__ = "issuer_status_publication_records"
    __table_args__ = (
        Index(
            "ix_issuer_status_publication_registry_version",
            "issuer_registry_id",
            "status_version",
            "created_at",
        ),
        Index(
            "ix_issuer_status_publication_status_created",
            "status",
            "created_at",
        ),
    )

    publication_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    issuer_registry_id: Mapped[str] = mapped_column(
        ForeignKey("issuer_registry_records.registry_id"),
        nullable=False,
    )
    status_version: Mapped[int] = mapped_column(Integer, nullable=False)
    standing: Mapped[IssuerStanding] = mapped_column(
        Enum(IssuerStanding, native_enum=False, validate_strings=True),
        nullable=False,
    )
    status: Mapped[IssuerStatusPublicationStatus] = mapped_column(
        Enum(
            IssuerStatusPublicationStatus,
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    status_reference: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
    )
    key_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    signing_input_digest: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    provider_operation_ref: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    status_artifact: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    actor_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    max_staleness_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class IssuerRegistryAuditEvent(Base):
    __tablename__ = "issuer_registry_audit_events"
    __table_args__ = (
        Index(
            "ix_issuer_registry_audit_registry_created",
            "issuer_registry_id",
            "created_at",
        ),
        Index(
            "ix_issuer_registry_audit_actor_created",
            "actor_principal_id",
            "created_at",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    issuer_registry_id: Mapped[str] = mapped_column(
        ForeignKey("issuer_registry_records.registry_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    prior_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    resulting_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


__all__ = [
    "IssuerRegistryAuditEvent",
    "IssuerRegistryRecord",
    "IssuerStanding",
    "IssuerStatusPublicationRecord",
    "IssuerStatusPublicationStatus",
]
