from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserStatus(enum.StrEnum):
    active = "active"
    suspended = "suspended"


class RoleScope(enum.StrEnum):
    platform = "platform"
    tenant = "tenant"


class MembershipStatus(enum.StrEnum):
    active = "active"
    suspended = "suspended"


class ServicePrincipalStatus(enum.StrEnum):
    active = "active"
    suspended = "suspended"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_status_created_at", "status", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    identity_provider_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform_role_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    auth_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=UserStatus.active,
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

    memberships: Mapped[list[TenantMembership]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("role_key", name="uq_roles_role_key"),
        Index("ix_roles_scope_tenant_id", "scope", "tenant_id"),
        Index("ix_roles_is_system", "is_system"),
    )

    role_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    role_key: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=True)
    scope: Mapped[RoleScope] = mapped_column(
        Enum(RoleScope, native_enum=False, validate_strings=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

    tenant = relationship("Tenant", back_populates="roles")


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_user"),
        Index("ix_tenant_memberships_tenant_status", "tenant_id", "status"),
        Index("ix_tenant_memberships_user_status", "user_id", "status"),
    )

    membership_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    role_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=MembershipStatus.active,
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

    tenant = relationship("Tenant", back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class ServicePrincipal(Base):
    __tablename__ = "service_principals"
    __table_args__ = (
        UniqueConstraint("principal_key", name="uq_service_principals_principal_key"),
        Index("ix_service_principals_tenant_status", "tenant_id", "status"),
    )

    service_principal_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    principal_key: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    auth_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ServicePrincipalStatus] = mapped_column(
        Enum(ServicePrincipalStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=ServicePrincipalStatus.active,
    )
    auth_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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

    tenant = relationship("Tenant", back_populates="service_principals")
