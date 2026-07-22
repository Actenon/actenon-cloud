"""Add RLS policy on authorised_execution_intents table (Prompt 14 fix).

Revision ID: 20260722_0014
Revises: 20260722_0013
Create Date: 2026-07-22 20:00:00
"""

from __future__ import annotations

from alembic import op

revision = "20260722_0014"
down_revision = "20260722_0013"
branch_labels = None
depends_on = None

# The AEI table uses requester_tenant_id (not tenant_id) for tenant scoping.
# We add RLS policies that match on requester_tenant_id.
TABLE_NAME = "authorised_execution_intents"


def _is_postgresql() -> bool:
    bind = op.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _policy_name(suffix: str) -> str:
    return f"{TABLE_NAME}_tenant_id_{suffix}"


def upgrade() -> None:
    if not _is_postgresql():
        # No-op on SQLite (the test backend). RLS is enforced in Python
        # via _validate_tenant_access for SQLite tests.
        return

    # Enable + FORCE RLS so even table owners respect it.
    op.execute(f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY")

    # USING policy: rows are visible if the requester_tenant_id matches
    # the session's current tenant scope.
    op.execute(
        f"""
        CREATE POLICY {_policy_name("using")}
        ON {TABLE_NAME}
        FOR ALL
        USING (
            requester_tenant_id = current_setting('app.tenant_id', true)::text
            OR current_setting('app.current_is_platform_admin', true) = 'true'
        )
        """
    )

    # WITH CHECK policy: new rows must have the correct tenant_id.
    op.execute(
        f"""
        CREATE POLICY {_policy_name("check")}
        ON {TABLE_NAME}
        FOR ALL
        WITH CHECK (
            requester_tenant_id = current_setting('app.tenant_id', true)::text
            OR current_setting('app.current_is_platform_admin', true) = 'true'
        )
        """
    )


def downgrade() -> None:
    if not _is_postgresql():
        return
    op.execute(f"DROP POLICY IF EXISTS {_policy_name('check')} ON {TABLE_NAME}")
    op.execute(f"DROP POLICY IF EXISTS {_policy_name('using')} ON {TABLE_NAME}")
    op.execute(f"ALTER TABLE {TABLE_NAME} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE_NAME} DISABLE ROW LEVEL SECURITY")
