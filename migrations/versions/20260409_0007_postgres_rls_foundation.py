"""Add PostgreSQL row-level security foundations for tenant-scoped workflow tables.

Revision ID: 20260409_0007
Revises: 20260406_0006
Create Date: 2026-04-09 12:10:00
"""
from __future__ import annotations

from alembic import op

revision = "20260409_0007"
down_revision = "20260406_0006"
branch_labels = None
depends_on = None

RLS_POLICY_NAME = "tenant_scope_policy"
RLS_FUNCTION_NAME = "acp_rls_tenant_visible"
TENANT_SCOPED_TABLES = (
    "tenants",
    "policies",
    "action_intent_records",
    "approval_requests",
    "approver_assignments",
    "approval_decisions",
    "evidence_objects",
    "signing_key_references",
    "issued_proofs",
    "signing_operation_records",
    "escrow_records",
    "escrow_transition_records",
    "receipt_records",
    "reconciliation_records",
    "audit_events",
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_tenant_visibility_function() -> None:
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {RLS_FUNCTION_NAME}(row_tenant_id text)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                COALESCE(current_setting('app.current_is_platform_admin', true), '') = 'true'
                OR row_tenant_id = ANY(
                    COALESCE(
                        string_to_array(
                            NULLIF(current_setting('app.current_tenant_scope', true), ''),
                            ','
                        ),
                        ARRAY[]::text[]
                    )
                )
        $$;
        """
    )


def _enable_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {RLS_POLICY_NAME}
        ON {table_name}
        FOR ALL
        USING ({RLS_FUNCTION_NAME}(tenant_id))
        WITH CHECK ({RLS_FUNCTION_NAME}(tenant_id))
        """
    )


def _disable_rls(table_name: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {RLS_POLICY_NAME} ON {table_name}")
    op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    if not _is_postgresql():
        return

    _create_tenant_visibility_function()
    for table_name in TENANT_SCOPED_TABLES:
        _enable_rls(table_name)


def downgrade() -> None:
    if not _is_postgresql():
        return

    for table_name in reversed(TENANT_SCOPED_TABLES):
        _disable_rls(table_name)
    op.execute(f"DROP FUNCTION IF EXISTS {RLS_FUNCTION_NAME}(text)")
