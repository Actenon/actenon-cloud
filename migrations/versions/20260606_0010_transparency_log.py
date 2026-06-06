"""Add durable digest-only transparency log records.

Revision ID: 20260606_0010
Revises: 20260606_0009
Create Date: 2026-06-06 15:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260606_0010"
down_revision = "20260606_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transparency_log_states",
        sa.Column("log_id", sa.String(length=512), nullable=False),
        sa.Column("log_identity", sa.JSON(), nullable=False),
        sa.Column("next_leaf_index", sa.Integer(), nullable=False),
        sa.Column("append_chain_head", sa.String(length=64), nullable=True),
        sa.Column("latest_checkpoint_size", sa.Integer(), nullable=True),
        sa.Column("latest_checkpoint_digest", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("log_id"),
    )

    op.create_table(
        "transparency_log_leaves",
        sa.Column("leaf_id", sa.String(length=32), nullable=False),
        sa.Column("log_id", sa.String(length=512), nullable=False),
        sa.Column("leaf_index", sa.Integer(), nullable=False),
        sa.Column("receipt_digest", sa.String(length=64), nullable=False),
        sa.Column("leaf_hash", sa.String(length=64), nullable=False),
        sa.Column("append_chain_hash", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("leaf_id"),
        sa.UniqueConstraint(
            "log_id",
            "leaf_index",
            name="uq_transparency_leaf_index",
        ),
        sa.UniqueConstraint(
            "log_id",
            "receipt_digest",
            name="uq_transparency_receipt_digest",
        ),
    )
    op.create_index(
        "ix_transparency_leaves_log_index",
        "transparency_log_leaves",
        ["log_id", "leaf_index"],
        unique=False,
    )

    op.create_table(
        "transparency_checkpoint_records",
        sa.Column("checkpoint_id", sa.String(length=32), nullable=False),
        sa.Column("log_id", sa.String(length=512), nullable=False),
        sa.Column("tree_size", sa.Integer(), nullable=False),
        sa.Column("root_hash", sa.String(length=64), nullable=False),
        sa.Column("key_id", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("signing_input_digest", sa.String(length=64), nullable=True),
        sa.Column("checkpoint_digest", sa.String(length=64), nullable=True),
        sa.Column("prior_checkpoint_digest", sa.String(length=64), nullable=True),
        sa.Column("provider_operation_ref", sa.String(length=1024), nullable=True),
        sa.Column("checkpoint_artifact", sa.JSON(), nullable=True),
        sa.Column("actor_principal_type", sa.String(length=32), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=255), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("checkpoint_id"),
        sa.UniqueConstraint(
            "log_id",
            "tree_size",
            name="uq_transparency_checkpoint_tree_size",
        ),
    )
    op.create_index(
        "ix_transparency_checkpoints_log_size",
        "transparency_checkpoint_records",
        ["log_id", "tree_size"],
        unique=False,
    )
    op.create_index(
        "ix_transparency_checkpoints_status_created",
        "transparency_checkpoint_records",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "transparency_integrity_events",
        sa.Column("event_id", sa.String(length=32), nullable=False),
        sa.Column("log_id", sa.String(length=512), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_transparency_integrity_log_detected",
        "transparency_integrity_events",
        ["log_id", "detected_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transparency_integrity_log_detected",
        table_name="transparency_integrity_events",
    )
    op.drop_table("transparency_integrity_events")

    op.drop_index(
        "ix_transparency_checkpoints_status_created",
        table_name="transparency_checkpoint_records",
    )
    op.drop_index(
        "ix_transparency_checkpoints_log_size",
        table_name="transparency_checkpoint_records",
    )
    op.drop_table("transparency_checkpoint_records")

    op.drop_index(
        "ix_transparency_leaves_log_index",
        table_name="transparency_log_leaves",
    )
    op.drop_table("transparency_log_leaves")
    op.drop_table("transparency_log_states")
