"""Add operated issuer registry and signed status publication records.

Revision ID: 20260606_0011
Revises: 20260606_0010
Create Date: 2026-06-06 17:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260606_0011"
down_revision = "20260606_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issuer_registry_records",
        sa.Column("registry_id", sa.String(length=32), nullable=False),
        sa.Column("issuer_type", sa.String(length=64), nullable=False),
        sa.Column("issuer_id", sa.String(length=512), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("standing", sa.String(length=32), nullable=False),
        sa.Column("standing_reason", sa.Text(), nullable=True),
        sa.Column("status_version", sa.Integer(), nullable=False),
        sa.Column("registry_metadata", sa.JSON(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("standing_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("registry_id"),
        sa.UniqueConstraint(
            "issuer_type",
            "issuer_id",
            name="uq_issuer_registry_identity",
        ),
    )
    op.create_index(
        "ix_issuer_registry_standing_updated",
        "issuer_registry_records",
        ["standing", "updated_at"],
        unique=False,
    )

    op.create_table(
        "issuer_status_publication_records",
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("issuer_registry_id", sa.String(length=32), nullable=False),
        sa.Column("status_version", sa.Integer(), nullable=False),
        sa.Column("standing", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("status_reference", sa.String(length=1024), nullable=False),
        sa.Column("key_id", sa.String(length=256), nullable=True),
        sa.Column("signing_input_digest", sa.String(length=64), nullable=True),
        sa.Column("provider_operation_ref", sa.String(length=1024), nullable=True),
        sa.Column("status_artifact", sa.JSON(), nullable=True),
        sa.Column("actor_principal_type", sa.String(length=32), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=255), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_staleness_seconds", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["issuer_registry_id"],
            ["issuer_registry_records.registry_id"],
        ),
        sa.PrimaryKeyConstraint("publication_id"),
        sa.UniqueConstraint("status_reference"),
    )
    op.create_index(
        "ix_issuer_status_publication_registry_version",
        "issuer_status_publication_records",
        ["issuer_registry_id", "status_version", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_issuer_status_publication_status_created",
        "issuer_status_publication_records",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "issuer_registry_audit_events",
        sa.Column("event_id", sa.String(length=32), nullable=False),
        sa.Column("issuer_registry_id", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_principal_type", sa.String(length=32), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("prior_state", sa.JSON(), nullable=True),
        sa.Column("resulting_state", sa.JSON(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["issuer_registry_id"],
            ["issuer_registry_records.registry_id"],
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_issuer_registry_audit_registry_created",
        "issuer_registry_audit_events",
        ["issuer_registry_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_issuer_registry_audit_actor_created",
        "issuer_registry_audit_events",
        ["actor_principal_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_issuer_registry_audit_actor_created",
        table_name="issuer_registry_audit_events",
    )
    op.drop_index(
        "ix_issuer_registry_audit_registry_created",
        table_name="issuer_registry_audit_events",
    )
    op.drop_table("issuer_registry_audit_events")

    op.drop_index(
        "ix_issuer_status_publication_status_created",
        table_name="issuer_status_publication_records",
    )
    op.drop_index(
        "ix_issuer_status_publication_registry_version",
        table_name="issuer_status_publication_records",
    )
    op.drop_table("issuer_status_publication_records")

    op.drop_index(
        "ix_issuer_registry_standing_updated",
        table_name="issuer_registry_records",
    )
    op.drop_table("issuer_registry_records")
