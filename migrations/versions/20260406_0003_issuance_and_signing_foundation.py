"""Add proof issuance and signing foundation tables.

Revision ID: 20260406_0003
Revises: 20260406_0002
Create Date: 2026-04-06 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0003"
down_revision = "20260406_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signing_key_references",
        sa.Column("signing_key_reference_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("issuer_name", sa.String(length=255), nullable=False),
        sa.Column("issuer_uri", sa.String(length=1024), nullable=False),
        sa.Column("trust_tier", sa.String(length=32), nullable=False),
        sa.Column("key_purpose", sa.String(length=32), nullable=False),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("key_backend", sa.String(length=32), nullable=False),
        sa.Column("provider_key_ref", sa.String(length=255), nullable=False),
        sa.Column("public_key_ref", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("lifecycle_metadata", sa.JSON(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("signing_key_reference_id"),
    )
    op.create_index(
        "ix_signing_key_references_tenant_purpose_status",
        "signing_key_references",
        ["tenant_id", "key_purpose", "status"],
        unique=False,
    )

    op.create_table(
        "issued_proofs",
        sa.Column("issued_proof_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("action_intent_record_id", sa.String(length=32), nullable=False),
        sa.Column("signing_key_reference_id", sa.String(length=32), nullable=True),
        sa.Column("proof_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("issuer_name", sa.String(length=255), nullable=False),
        sa.Column("issuer_uri", sa.String(length=1024), nullable=False),
        sa.Column("trust_tier", sa.String(length=32), nullable=False),
        sa.Column("audience", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("scope_hash", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("action_intent_digest", sa.String(length=64), nullable=False),
        sa.Column("proof_payload", sa.JSON(), nullable=False),
        sa.Column("proof_payload_digest", sa.String(length=64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("algorithm", sa.String(length=32), nullable=True),
        sa.Column("issued_by_principal_type", sa.String(length=32), nullable=False),
        sa.Column("issued_by_principal_id", sa.String(length=255), nullable=False),
        sa.Column("issuance_trace", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("revocation_reason_code", sa.String(length=255), nullable=True),
        sa.Column("revocation_reason_detail", sa.Text(), nullable=True),
        sa.Column("revocation_reference", sa.String(length=255), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_intent_record_id"], ["action_intent_records.action_intent_record_id"]
        ),
        sa.ForeignKeyConstraint(
            ["signing_key_reference_id"], ["signing_key_references.signing_key_reference_id"]
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("issued_proof_id"),
    )
    op.create_index(
        "ix_issued_proofs_tenant_action_intent_created_at",
        "issued_proofs",
        ["tenant_id", "action_intent_record_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_issued_proofs_tenant_status",
        "issued_proofs",
        ["tenant_id", "status"],
        unique=False,
    )

    op.create_table(
        "signing_operation_records",
        sa.Column("signing_operation_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("issued_proof_id", sa.String(length=32), nullable=False),
        sa.Column("signing_key_reference_id", sa.String(length=32), nullable=False),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("key_backend", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("provider_operation_ref", sa.String(length=255), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["issued_proof_id"], ["issued_proofs.issued_proof_id"]),
        sa.ForeignKeyConstraint(
            ["signing_key_reference_id"], ["signing_key_references.signing_key_reference_id"]
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("signing_operation_id"),
    )
    op.create_index(
        "ix_signing_operation_records_tenant_created_at",
        "signing_operation_records",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_signing_operation_records_tenant_created_at",
        table_name="signing_operation_records",
    )
    op.drop_table("signing_operation_records")
    op.drop_index("ix_issued_proofs_tenant_status", table_name="issued_proofs")
    op.drop_index(
        "ix_issued_proofs_tenant_action_intent_created_at",
        table_name="issued_proofs",
    )
    op.drop_table("issued_proofs")
    op.drop_index(
        "ix_signing_key_references_tenant_purpose_status",
        table_name="signing_key_references",
    )
    op.drop_table("signing_key_references")
