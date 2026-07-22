"""Initial tenant, policy, and Action Intent intake tables.

Revision ID: 20260406_0001
Revises:
Create Date: 2026-04-06 12:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("finance_profile", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id"),
    )

    op.create_table(
        "policies",
        sa.Column("policy_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workflow_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("default_decision", sa.String(length=64), nullable=False),
        sa.Column("finance_action_classes", sa.JSON(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("policy_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "workflow_key",
            "version",
            name="uq_policies_tenant_workflow_version",
        ),
    )
    op.create_index(
        "ix_policies_tenant_workflow_status",
        "policies",
        ["tenant_id", "workflow_key", "status"],
        unique=False,
    )

    op.create_table(
        "action_intent_records",
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("policy_id", sa.String(length=32), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column("submission_id", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("requested_by_principal_type", sa.String(length=32), nullable=False),
        sa.Column("requested_by_principal_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_key", sa.String(length=255), nullable=False),
        sa.Column("external_action_intent_id", sa.String(length=255), nullable=True),
        sa.Column("contract_family", sa.String(length=64), nullable=False),
        sa.Column("contract_version_ref", sa.String(length=255), nullable=False),
        sa.Column("contract_validation_status", sa.String(length=32), nullable=False),
        sa.Column("contract_validation_errors", sa.JSON(), nullable=False),
        sa.Column("action_intent_digest", sa.String(length=64), nullable=False),
        sa.Column("action_intent_payload", sa.JSON(), nullable=False),
        sa.Column("workflow_binding", sa.JSON(), nullable=True),
        sa.Column("finance_routing_context", sa.JSON(), nullable=True),
        sa.Column("finance_action_class", sa.String(length=64), nullable=True),
        sa.Column("finance_index", sa.JSON(), nullable=False),
        sa.Column("evaluation_context", sa.JSON(), nullable=False),
        sa.Column("client_tags", sa.JSON(), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("decision_state", sa.String(length=64), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("matched_rule_id", sa.String(length=255), nullable=True),
        sa.Column("evaluation_trace", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.policy_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("action_intent_record_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_action_intent_records_tenant_idempotency_key",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "submission_id",
            name="uq_action_intent_records_tenant_submission_id",
        ),
    )
    op.create_index(
        "ix_action_intent_records_tenant_created_at",
        "action_intent_records",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_action_intent_records_tenant_workflow",
        "action_intent_records",
        ["tenant_id", "workflow_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_action_intent_records_tenant_workflow", table_name="action_intent_records")
    op.drop_index("ix_action_intent_records_tenant_created_at", table_name="action_intent_records")
    op.drop_table("action_intent_records")
    op.drop_index("ix_policies_tenant_workflow_status", table_name="policies")
    op.drop_table("policies")
    op.drop_table("tenants")
