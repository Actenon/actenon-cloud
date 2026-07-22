"""Add managed receipt counter-signing keys and audit records.

Revision ID: 20260606_0009
Revises: 20260410_0008
Create Date: 2026-06-06 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260606_0009"
down_revision = "20260410_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "counter_signing_keys",
        sa.Column("key_id", sa.String(length=256), nullable=False),
        sa.Column("provider_key_ref", sa.String(length=1024), nullable=False),
        sa.Column("public_key_jwk", sa.JSON(), nullable=False),
        sa.Column("witness", sa.JSON(), nullable=False),
        sa.Column("origin", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_key_id", sa.String(length=256), nullable=True),
        sa.Column("provider_attestation_ref", sa.String(length=1024), nullable=True),
        sa.Column("lifecycle_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key_id"),
        sa.UniqueConstraint("provider_key_ref"),
    )
    op.create_index(
        "ix_counter_signing_keys_status_created_at",
        "counter_signing_keys",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "counter_signing_operation_records",
        sa.Column("operation_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=True),
        sa.Column("receipt_id", sa.String(length=255), nullable=True),
        sa.Column("receipt_digest", sa.String(length=64), nullable=False),
        sa.Column("signing_input_digest", sa.String(length=64), nullable=True),
        sa.Column("key_id", sa.String(length=256), nullable=True),
        sa.Column("actor_principal_type", sa.String(length=32), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_operation_ref", sa.String(length=1024), nullable=True),
        sa.Column("countersignature_artifact", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("operation_id"),
    )
    op.create_index(
        "ix_counter_signing_operations_status_created_at",
        "counter_signing_operation_records",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_counter_signing_operations_receipt_digest",
        "counter_signing_operation_records",
        ["receipt_digest"],
        unique=False,
    )
    op.create_index(
        "ix_counter_signing_operations_actor",
        "counter_signing_operation_records",
        ["actor_principal_type", "actor_principal_id"],
        unique=False,
    )

    op.create_table(
        "counter_signing_lifecycle_records",
        sa.Column("lifecycle_operation_id", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("target_key_id", sa.String(length=256), nullable=False),
        sa.Column("prior_key_id", sa.String(length=256), nullable=True),
        sa.Column("requester_principal_type", sa.String(length=32), nullable=False),
        sa.Column("requester_principal_id", sa.String(length=255), nullable=False),
        sa.Column("approver_principal_ids", sa.JSON(), nullable=False),
        sa.Column("provider_operation_ref", sa.String(length=1024), nullable=True),
        sa.Column("published_key_set_digest", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("lifecycle_operation_id"),
    )
    op.create_index(
        "ix_counter_signing_lifecycle_action_created_at",
        "counter_signing_lifecycle_records",
        ["action", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_counter_signing_lifecycle_target_key",
        "counter_signing_lifecycle_records",
        ["target_key_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_counter_signing_lifecycle_target_key",
        table_name="counter_signing_lifecycle_records",
    )
    op.drop_index(
        "ix_counter_signing_lifecycle_action_created_at",
        table_name="counter_signing_lifecycle_records",
    )
    op.drop_table("counter_signing_lifecycle_records")

    op.drop_index(
        "ix_counter_signing_operations_actor",
        table_name="counter_signing_operation_records",
    )
    op.drop_index(
        "ix_counter_signing_operations_receipt_digest",
        table_name="counter_signing_operation_records",
    )
    op.drop_index(
        "ix_counter_signing_operations_status_created_at",
        table_name="counter_signing_operation_records",
    )
    op.drop_table("counter_signing_operation_records")

    op.drop_index(
        "ix_counter_signing_keys_status_created_at",
        table_name="counter_signing_keys",
    )
    op.drop_table("counter_signing_keys")
