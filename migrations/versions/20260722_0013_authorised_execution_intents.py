"""Add authorised_execution_intents table (Prompt 10).

Revision ID: 20260722_0013
Revises: 20260709_0012
Create Date: 2026-07-22 13:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260722_0013"
down_revision = "20260709_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authorised_execution_intents",
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("requester_subject", sa.String(length=255), nullable=False),
        sa.Column("requester_tenant_id", sa.String(length=64), nullable=True),
        sa.Column("requested_execution_mode", sa.String(length=32), nullable=False),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=False),
        sa.Column("linked_proof_id", sa.String(length=64), nullable=True),
        sa.Column("linked_receipt_id", sa.String(length=64), nullable=True),
        sa.Column("linked_refusal_id", sa.String(length=64), nullable=True),
        sa.Column("submission_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("intent_id", name="pk_authorised_execution_intents"),
    )
    op.create_index(
        "ix_aei_requester_subject_created_at",
        "authorised_execution_intents",
        ["requester_subject", "created_at"],
    )
    op.create_index(
        "ix_aei_lifecycle_state",
        "authorised_execution_intents",
        ["lifecycle_state"],
    )


def downgrade() -> None:
    op.drop_index("ix_aei_lifecycle_state", table_name="authorised_execution_intents")
    op.drop_index(
        "ix_aei_requester_subject_created_at", table_name="authorised_execution_intents"
    )
    op.drop_table("authorised_execution_intents")
