"""Add capability escrow foundation tables and execution state.

Revision ID: 20260406_0004
Revises: 20260406_0003
Create Date: 2026-04-06 19:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0004"
down_revision = "20260406_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("action_intent_records") as batch_op:
        batch_op.add_column(
            sa.Column(
                "execution_state",
                sa.String(length=32),
                nullable=False,
                server_default="not_requested",
            )
        )

    op.create_table(
        "escrow_records",
        sa.Column("escrow_record_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=False),
        sa.Column("issued_proof_id", sa.String(length=32), nullable=False),
        sa.Column("capability_kind", sa.String(length=255), nullable=False),
        sa.Column("protected_resource_ref", sa.String(length=1024), nullable=False),
        sa.Column("release_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("execution_state", sa.String(length=32), nullable=False),
        sa.Column("audience", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("scope_hash", sa.String(length=64), nullable=False),
        sa.Column("action_intent_digest", sa.String(length=64), nullable=False),
        sa.Column("proof_nonce", sa.String(length=64), nullable=False),
        sa.Column("created_by_principal_type", sa.String(length=32), nullable=False),
        sa.Column("created_by_principal_id", sa.String(length=255), nullable=False),
        sa.Column("capability_reference", sa.String(length=255), nullable=True),
        sa.Column("capability_token_digest", sa.String(length=64), nullable=True),
        sa.Column("capability_metadata", sa.JSON(), nullable=False),
        sa.Column("release_metadata", sa.JSON(), nullable=False),
        sa.Column("provider_execution_ref", sa.String(length=255), nullable=True),
        sa.Column("provider_status", sa.String(length=255), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("revocation_reason_code", sa.String(length=255), nullable=True),
        sa.Column("revocation_reason_detail", sa.Text(), nullable=True),
        sa.Column("quarantine_reason_code", sa.String(length=255), nullable=True),
        sa.Column("quarantine_reason_detail", sa.Text(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_intent_record_id"], ["action_intent_records.action_intent_record_id"]
        ),
        sa.ForeignKeyConstraint(["issued_proof_id"], ["issued_proofs.issued_proof_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("escrow_record_id"),
        sa.UniqueConstraint("issued_proof_id", name="uq_escrow_records_issued_proof"),
    )
    op.create_index(
        "ix_escrow_records_tenant_status",
        "escrow_records",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_escrow_records_action_intent_execution_state",
        "escrow_records",
        ["action_intent_record_id", "execution_state"],
        unique=False,
    )

    op.create_table(
        "escrow_transition_records",
        sa.Column("escrow_transition_record_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("escrow_record_id", sa.String(length=32), nullable=False),
        sa.Column("transition_type", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("from_execution_state", sa.String(length=32), nullable=True),
        sa.Column("to_execution_state", sa.String(length=32), nullable=False),
        sa.Column("actor_principal_type", sa.String(length=32), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=255), nullable=False),
        sa.Column("reason_code", sa.String(length=255), nullable=True),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("transition_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["escrow_record_id"], ["escrow_records.escrow_record_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("escrow_transition_record_id"),
    )
    op.create_index(
        "ix_escrow_transition_records_escrow_created_at",
        "escrow_transition_records",
        ["escrow_record_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_escrow_transition_records_tenant_created_at",
        "escrow_transition_records",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_escrow_transition_records_tenant_created_at",
        table_name="escrow_transition_records",
    )
    op.drop_index(
        "ix_escrow_transition_records_escrow_created_at",
        table_name="escrow_transition_records",
    )
    op.drop_table("escrow_transition_records")
    op.drop_index(
        "ix_escrow_records_action_intent_execution_state",
        table_name="escrow_records",
    )
    op.drop_index("ix_escrow_records_tenant_status", table_name="escrow_records")
    op.drop_table("escrow_records")

    with op.batch_alter_table("action_intent_records") as batch_op:
        batch_op.drop_column("execution_state")
