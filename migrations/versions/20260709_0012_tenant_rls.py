"""B5: enable Postgres RLS on every tenant-scoped table with a tenant_id policy.

This migration supplements the earlier ``20260409_0007_postgres_rls_foundation``
migration. The foundation migration created a single ``tenant_scope_policy``
that delegates visibility to a ``acp_rls_tenant_visible(row_tenant_id)``
function backed by the ``app.current_tenant_scope`` setting (a comma-separated
list). That works for platform admins and tenants with explicit comma-listed
scope, but it does not implement the simpler single-tenant
``app.tenant_id`` session-setting contract that production deployments rely on.

This migration adds, for every tenant-scoped table:

  * ``ENABLE ROW LEVEL SECURITY`` (and ``FORCE`` so even table owners respect it)
  * a ``tenant_id USING`` policy that reads ``current_setting('app.tenant_id', true)``
  * a ``tenant_id WITH CHECK`` policy that enforces the same setting on writes

The migration is a no-op on SQLite (the test/local backend): every
``op.execute`` call is guarded by a dialect check so the migration is safe to
run on the SQLite test backend, which does not support RLS.

Revision ID: 20260709_0012
Revises: 20260606_0011
Create Date: 2026-07-09 10:00:00
"""

from __future__ import annotations

from alembic import op

revision = "20260709_0012"
down_revision = "20260606_0011"
branch_labels = None
depends_on = None


# Every tenant-scoped table that owns a ``tenant_id`` column. The list mirrors
# the tenant-scoped tables enumerated in the B5 brief (with the addition of
# the tenants table itself, whose own tenant_id column is the table's primary
# key and therefore participates in the same RLS contract).
TENANT_SCOPED_TABLES = (
    "tenants",
    "action_intent_records",
    "policies",
    "approval_requests",
    "evidence_objects",
    "issued_proofs",
    "receipt_records",
    "escrow_records",
    "signing_key_references",
    "audit_events",
)


def _is_postgresql() -> bool:
    bind = op.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _policy_name(table_name: str, suffix: str) -> str:
    return f"{table_name}_tenant_id_{suffix}"


def _enable_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def _create_using_policy(table_name: str) -> None:
    op.execute(
        f"""
        CREATE POLICY {_policy_name(table_name, "using")}
        ON {table_name}
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id', true)::text)
        """
    )


def _create_with_check_policy(table_name: str) -> None:
    op.execute(
        f"""
        CREATE POLICY {_policy_name(table_name, "check")}
        ON {table_name}
        FOR ALL
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::text)
        """
    )


def _drop_policies(table_name: str) -> None:
    op.execute(
        f"DROP POLICY IF EXISTS {_policy_name(table_name, 'check')} ON {table_name}"
    )
    op.execute(
        f"DROP POLICY IF EXISTS {_policy_name(table_name, 'using')} ON {table_name}"
    )


def _disable_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    # The migration is a no-op on SQLite (and any non-postgres backend): RLS
    # is a PostgreSQL feature, and the test/local SQLite backend does not
    # support it. Guarding here keeps the migration safe to run everywhere.
    if not _is_postgresql():
        return

    for table_name in TENANT_SCOPED_TABLES:
        _enable_rls(table_name)
        _create_using_policy(table_name)
        _create_with_check_policy(table_name)


def downgrade() -> None:
    if not _is_postgresql():
        return

    for table_name in reversed(TENANT_SCOPED_TABLES):
        _drop_policies(table_name)
        _disable_rls(table_name)
