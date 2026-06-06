"""Add approval workflow and evidence intake tables.

Revision ID: 20260406_0002
Revises: 20260406_0001
Create Date: 2026-04-06 16:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0002"
down_revision = "20260406_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "action_intent_records",
        sa.Column(
            "approval_state",
            sa.String(length=32),
            nullable=False,
            server_default="not_required",
        ),
    )
    op.add_column(
        "action_intent_records",
        sa.Column(
            "evidence_state",
            sa.String(length=32),
            nullable=False,
            server_default="not_required",
        ),
    )
    op.add_column(
        "action_intent_records",
        sa.Column("approval_requirement", sa.JSON(), nullable=True),
    )
    op.add_column(
        "action_intent_records",
        sa.Column("evidence_requirement", sa.JSON(), nullable=True),
    )

    op.create_table(
        "approval_requests",
        sa.Column("approval_request_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=False),
        sa.Column("policy_id", sa.String(length=32), nullable=True),
        sa.Column("workflow_rule_id", sa.String(length=255), nullable=True),
        sa.Column("approval_group_key", sa.String(length=255), nullable=False),
        sa.Column("required_decision_count", sa.Integer(), nullable=False),
        sa.Column("eligible_role_ids", sa.JSON(), nullable=False),
        sa.Column("separation_of_duties", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("satisfied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_intent_record_id"], ["action_intent_records.action_intent_record_id"]
        ),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.policy_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("approval_request_id"),
    )
    op.create_index(
        "ix_approval_requests_tenant_status",
        "approval_requests",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_approval_requests_action_intent_status",
        "approval_requests",
        ["action_intent_record_id", "status"],
        unique=False,
    )

    op.create_table(
        "approver_assignments",
        sa.Column("approval_assignment_id", sa.String(length=32), nullable=False),
        sa.Column("approval_request_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("principal_type", sa.String(length=32), nullable=False),
        sa.Column("principal_id", sa.String(length=255), nullable=False),
        sa.Column("assignment_status", sa.String(length=32), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.approval_request_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("approval_assignment_id"),
        sa.UniqueConstraint(
            "approval_request_id",
            "principal_type",
            "principal_id",
            name="uq_approver_assignments_request_principal",
        ),
    )
    op.create_index(
        "ix_approver_assignments_tenant_principal_status",
        "approver_assignments",
        ["tenant_id", "principal_id", "assignment_status"],
        unique=False,
    )

    op.create_table(
        "approval_decisions",
        sa.Column("approval_decision_id", sa.String(length=32), nullable=False),
        sa.Column("approval_request_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("decided_by_principal_type", sa.String(length=32), nullable=False),
        sa.Column("decided_by_principal_id", sa.String(length=255), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("evidence_object_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.approval_request_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("approval_decision_id"),
        sa.UniqueConstraint(
            "approval_request_id",
            "decided_by_principal_type",
            "decided_by_principal_id",
            name="uq_approval_decisions_request_principal",
        ),
    )
    op.create_index(
        "ix_approval_decisions_request_created_at",
        "approval_decisions",
        ["approval_request_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "evidence_objects",
        sa.Column("evidence_object_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=False),
        sa.Column("approval_request_id", sa.String(length=32), nullable=True),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("storage_mode", sa.String(length=32), nullable=False),
        sa.Column("storage_ref", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("media_type", sa.String(length=255), nullable=True),
        sa.Column("content_digest", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_by_principal_type", sa.String(length=32), nullable=False),
        sa.Column("uploaded_by_principal_id", sa.String(length=255), nullable=False),
        sa.Column("evidence_metadata", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_intent_record_id"], ["action_intent_records.action_intent_record_id"]
        ),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.approval_request_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("evidence_object_id"),
    )
    op.create_index(
        "ix_evidence_objects_tenant_action_intent",
        "evidence_objects",
        ["tenant_id", "action_intent_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_objects_approval_request",
        "evidence_objects",
        ["approval_request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_objects_approval_request", table_name="evidence_objects")
    op.drop_index("ix_evidence_objects_tenant_action_intent", table_name="evidence_objects")
    op.drop_table("evidence_objects")
    op.drop_index("ix_approval_decisions_request_created_at", table_name="approval_decisions")
    op.drop_table("approval_decisions")
    op.drop_index(
        "ix_approver_assignments_tenant_principal_status",
        table_name="approver_assignments",
    )
    op.drop_table("approver_assignments")
    op.drop_index("ix_approval_requests_action_intent_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_tenant_status", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_column("action_intent_records", "evidence_requirement")
    op.drop_column("action_intent_records", "approval_requirement")
    op.drop_column("action_intent_records", "evidence_state")
    op.drop_column("action_intent_records", "approval_state")
