"""Add active proof issuance idempotency guard.

Revision ID: 20260410_0008
Revises: 20260409_0007
Create Date: 2026-04-10 09:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260410_0008"
down_revision = "20260409_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_issued_proofs_active_idempotency",
        "issued_proofs",
        [
            "tenant_id",
            "action_intent_record_id",
            "proof_kind",
            "audience",
            "scope_hash",
            "action_intent_digest",
        ],
        unique=True,
        sqlite_where=sa.text("status IN ('requested', 'issued')"),
        postgresql_where=sa.text("status IN ('requested', 'issued')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_issued_proofs_active_idempotency",
        table_name="issued_proofs",
    )
