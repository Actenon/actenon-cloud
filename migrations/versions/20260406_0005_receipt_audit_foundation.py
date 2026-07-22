"""Add receipt, reconciliation, and audit foundation tables.

Revision ID: 20260406_0005
Revises: 20260406_0004
Create Date: 2026-04-06 21:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0005"
down_revision = "20260406_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("action_intent_records") as batch_op:
        batch_op.add_column(
            sa.Column(
                "receipt_state",
                sa.String(length=32),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.add_column(sa.Column("latest_receipt_id", sa.String(length=32), nullable=True))

    op.create_table(
        "receipt_records",
        sa.Column("receipt_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=False),
        sa.Column("issued_proof_id", sa.String(length=32), nullable=True),
        sa.Column("escrow_record_id", sa.String(length=32), nullable=True),
        sa.Column("contract_family", sa.String(length=64), nullable=False),
        sa.Column("contract_version_ref", sa.String(length=255), nullable=False),
        sa.Column("contract_validation_status", sa.String(length=32), nullable=False),
        sa.Column("contract_validation_errors", sa.JSON(), nullable=False),
        sa.Column("external_receipt_id", sa.String(length=255), nullable=False),
        sa.Column("receipt_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("receipt_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kernel_receipt_digest", sa.String(length=64), nullable=False),
        sa.Column("receipt_payload", sa.JSON(), nullable=False),
        sa.Column("receipt_index", sa.JSON(), nullable=False),
        sa.Column("linked_approval_request_ids", sa.JSON(), nullable=False),
        sa.Column("linked_approval_decision_ids", sa.JSON(), nullable=False),
        sa.Column("linked_evidence_object_ids", sa.JSON(), nullable=False),
        sa.Column("provider_execution_ref", sa.String(length=255), nullable=True),
        sa.Column("settlement_reference", sa.String(length=255), nullable=True),
        sa.Column("received_by_principal_type", sa.String(length=32), nullable=False),
        sa.Column("received_by_principal_id", sa.String(length=255), nullable=False),
        sa.Column("receipt_state", sa.String(length=32), nullable=False),
        sa.Column("reconciliation_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_intent_record_id"], ["action_intent_records.action_intent_record_id"]
        ),
        sa.ForeignKeyConstraint(["escrow_record_id"], ["escrow_records.escrow_record_id"]),
        sa.ForeignKeyConstraint(["issued_proof_id"], ["issued_proofs.issued_proof_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("receipt_id"),
        sa.UniqueConstraint(
            "tenant_id", "kernel_receipt_digest", name="uq_receipt_records_tenant_digest"
        ),
    )
    op.create_index(
        "ix_receipt_records_tenant_action_intent_timestamp",
        "receipt_records",
        ["tenant_id", "action_intent_record_id", "receipt_timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_receipt_records_tenant_type_outcome",
        "receipt_records",
        ["tenant_id", "receipt_type", "outcome"],
        unique=False,
    )
    op.create_index(
        "ix_receipt_records_provider_execution_ref",
        "receipt_records",
        ["provider_execution_ref"],
        unique=False,
    )

    op.create_table(
        "reconciliation_records",
        sa.Column("reconciliation_record_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=False),
        sa.Column("receipt_id", sa.String(length=32), nullable=False),
        sa.Column("issued_proof_id", sa.String(length=32), nullable=True),
        sa.Column("escrow_record_id", sa.String(length=32), nullable=True),
        sa.Column("reconciliation_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("hook_name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_intent_record_id"], ["action_intent_records.action_intent_record_id"]
        ),
        sa.ForeignKeyConstraint(["escrow_record_id"], ["escrow_records.escrow_record_id"]),
        sa.ForeignKeyConstraint(["issued_proof_id"], ["issued_proofs.issued_proof_id"]),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipt_records.receipt_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("reconciliation_record_id"),
    )
    op.create_index(
        "ix_reconciliation_records_action_intent_created_at",
        "reconciliation_records",
        ["action_intent_record_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_reconciliation_records_tenant_type_status",
        "reconciliation_records",
        ["tenant_id", "reconciliation_type", "status"],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=True),
        sa.Column("receipt_id", sa.String(length=32), nullable=True),
        sa.Column("issued_proof_id", sa.String(length=32), nullable=True),
        sa.Column("escrow_record_id", sa.String(length=32), nullable=True),
        sa.Column("event_category", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("actor_principal_type", sa.String(length=32), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=255), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_intent_record_id"], ["action_intent_records.action_intent_record_id"]
        ),
        sa.ForeignKeyConstraint(["escrow_record_id"], ["escrow_records.escrow_record_id"]),
        sa.ForeignKeyConstraint(["issued_proof_id"], ["issued_proofs.issued_proof_id"]),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipt_records.receipt_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("audit_event_id"),
    )
    op.create_index(
        "ix_audit_events_tenant_created_at",
        "audit_events",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_action_intent_event_type",
        "audit_events",
        ["action_intent_record_id", "event_type"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_subject",
        "audit_events",
        ["subject_type", "subject_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_subject", table_name="audit_events")
    op.drop_index("ix_audit_events_action_intent_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_tenant_created_at", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index(
        "ix_reconciliation_records_tenant_type_status",
        table_name="reconciliation_records",
    )
    op.drop_index(
        "ix_reconciliation_records_action_intent_created_at",
        table_name="reconciliation_records",
    )
    op.drop_table("reconciliation_records")

    op.drop_index(
        "ix_receipt_records_provider_execution_ref",
        table_name="receipt_records",
    )
    op.drop_index(
        "ix_receipt_records_tenant_type_outcome",
        table_name="receipt_records",
    )
    op.drop_index(
        "ix_receipt_records_tenant_action_intent_timestamp",
        table_name="receipt_records",
    )
    op.drop_table("receipt_records")

    with op.batch_alter_table("action_intent_records") as batch_op:
        batch_op.drop_column("latest_receipt_id")
        batch_op.drop_column("receipt_state")
