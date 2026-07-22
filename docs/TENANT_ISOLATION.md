# Tenant Isolation

## Isolation Boundary

`tenant_id` is the primary data and authorization boundary for the Actenon
Cloud/control-plane service.

Tenant isolation is trust-critical. It is not dashboard polish: a proof issuer,
approval store, evidence store, receipt fabric, or audit system that leaks
across tenants cannot safely act as a trust control plane.

## Tenant-Scoped Entities

The control plane treats these entities as tenant-scoped:

- tenants
- users/operators through tenant memberships and tenant roles
- tenant-scoped service principals
- policies
- Action Intent intake records
- approval requests, assignments, and decisions
- evidence objects and evidence content handles
- signing key references
- issued proofs and signing operation records
- escrow records and escrow transition records
- receipts/refusals represented as receipt records and failure/receipt audit
  records
- reconciliation records
- audit events and trace exports
- usage/metering summaries derived from tenant-scoped Action Intent and Receipt
  records

## API Enforcement

The current implementation enforces tenant isolation at the API edge through the
authenticated session model:

- platform administrators may operate across tenants
- tenant operators may operate only within tenants granted by membership
- tenant-scoped service principals may operate only within the bound tenant

For non-platform principals:

- list/search endpoints either infer the single tenant in the authenticated
  session or require an explicit `tenant_id`
- direct object endpoints load the object and authorize against the object's
  stored `tenant_id`
- mutation endpoints authorize the tenant before changing state
- cross-tenant object references fail closed at the service layer

## Database/RLS Support

The persistence model carries `tenant_id` on primary workflow, proof, evidence,
receipt, reconciliation, escrow, and audit records. Migration
`20260409_0007_postgres_rls_foundation.py` defines a PostgreSQL row-level
security foundation for the tenant-scoped tables and uses the request/session
RLS context:

- `app.current_tenant_scope`
- `app.current_is_platform_admin`
- `app.current_principal_id`

Current automated coverage includes unit tests that verify the RLS context is
normalized and applied to PostgreSQL connections, and skipped for SQLite
connections.

This pass did not run a live PostgreSQL/RLS integration environment. Before
production, the same two-tenant isolation matrix must be executed against
PostgreSQL with RLS enabled, including missing session context and forged
tenant-context cases.

## Tested Isolation Matrix

`tests/integration/test_tenant_isolation.py` uses the SQLite/in-process test
harness and two tenant-local operator tokens. It proves:

- tenant A cannot read tenant B Action Intent records
- tenant A cannot read tenant B evidence objects
- tenant A cannot read tenant B receipts
- tenant A cannot mutate tenant B policies
- tenant A cannot approve tenant B actions
- tenant A cannot query tenant B audit events or traces
- tenant A cannot query tenant B usage summaries
- forged `tenant_id` mutations are rejected
- cross-tenant object references are rejected
- missing tenant context for non-platform callers fails closed

## Platform Exception

Platform administrators exist to operate the hosted control plane. They are the
only currently implemented principal type with cross-tenant visibility by
default.

That exception is explicit and auditable. It is not the default for normal
tenant operators or tenant-scoped service principals.

## Known Gaps

- Live PostgreSQL/RLS enforcement still needs a production-like integration
  test run before production claims.
- Per-tenant encryption key separation is not implemented in this service.
- Some workflow actor fields are still caller-supplied for provenance and need
  stricter authenticated-session binding in a later hardening pass.
- There is not yet an organization hierarchy above the tenant boundary.
- Break-glass platform-admin workflows need additional approval, logging, and
  review policy before enterprise production operation.

## Production Follow-On

Before full enterprise rollout, tenant isolation should be strengthened with:

- live PostgreSQL/RLS tenant-isolation tests in CI or deployment verification
- per-tenant key management strategy
- end-to-end actor binding for all mutations
- stronger cross-tenant admin approvals and break-glass governance
- export job controls and tenant-bound data egress policies
