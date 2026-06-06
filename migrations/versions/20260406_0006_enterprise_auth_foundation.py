"""Add enterprise auth, admin, and tenancy foundation tables.

Revision ID: 20260406_0006
Revises: 20260406_0005
Create Date: 2026-04-06 22:10:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0006"
down_revision = "20260406_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("identity_provider_subject", sa.String(length=255), nullable=True),
        sa.Column("platform_role_ids", sa.JSON(), nullable=False),
        sa.Column("auth_metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_status_created_at", "users", ["status", "created_at"], unique=False)

    op.create_table(
        "roles",
        sa.Column("role_id", sa.String(length=32), nullable=False),
        sa.Column("role_key", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("role_id"),
        sa.UniqueConstraint("role_key", name="uq_roles_role_key"),
    )
    op.create_index("ix_roles_scope_tenant_id", "roles", ["scope", "tenant_id"], unique=False)
    op.create_index("ix_roles_is_system", "roles", ["is_system"], unique=False)

    op.create_table(
        "tenant_memberships",
        sa.Column("membership_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("role_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("membership_id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_user"),
    )
    op.create_index(
        "ix_tenant_memberships_tenant_status",
        "tenant_memberships",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_memberships_user_status",
        "tenant_memberships",
        ["user_id", "status"],
        unique=False,
    )

    op.create_table(
        "service_principals",
        sa.Column("service_principal_id", sa.String(length=32), nullable=False),
        sa.Column("principal_key", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("role_ids", sa.JSON(), nullable=False),
        sa.Column("auth_mode", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("auth_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("service_principal_id"),
        sa.UniqueConstraint("principal_key", name="uq_service_principals_principal_key"),
    )
    op.create_index(
        "ix_service_principals_tenant_status",
        "service_principals",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_service_principals_tenant_status", table_name="service_principals")
    op.drop_table("service_principals")

    op.drop_index("ix_tenant_memberships_user_status", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_tenant_status", table_name="tenant_memberships")
    op.drop_table("tenant_memberships")

    op.drop_index("ix_roles_is_system", table_name="roles")
    op.drop_index("ix_roles_scope_tenant_id", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_users_status_created_at", table_name="users")
    op.drop_table("users")
