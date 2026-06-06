# Multi-Tenancy Model

## Purpose

This document defines tenant isolation and tenancy behavior for Actenon Cloud.

## Primary Tenancy Boundary

`Tenant` is the primary boundary for:

- Action Intent intake
- policy packs and workflow rules
- approvals and evidence
- receipts and proof records
- revocation and quarantine controls
- audit and export data

Release 1 should assume every governed business record belongs to exactly one tenant.

## User And Membership Model

- A `User` may belong to multiple tenants.
- A `TenantMembership` determines which roles and approval entitlements the user has inside a tenant.
- Approver eligibility is always tenant-scoped even if the underlying user identity is reused across tenants.
- Service principals, if introduced, should follow the same tenant-scoped membership and role pattern.

## Isolation Rules

### Data Isolation

- Every tenant-scoped row carries `tenant_id`.
- Canonical payload storage keys should include tenant partitioning or an equivalent isolation boundary.
- Search indexes and export jobs must be filtered by tenant boundary by default.

### Policy Isolation

- Policy packs are tenant-owned unless explicitly defined as platform templates.
- Activation of a policy pack for one tenant must not affect another tenant.
- Approval thresholds and finance limits are tenant-local data.

### Key Isolation

- Signing key references should default to tenant-local scope.
- Shared platform keys, if any, must be explicitly designated and auditable.
- A tenant must never gain visibility into another tenant’s key references or signing history.

### Evidence Isolation

- Evidence objects must remain tenant-scoped even when stored in shared infrastructure.
- External references, filesystem-backed evidence paths, and any object-store keys must be access-controlled by tenant context.

## Administrative Boundaries

There should be at least three administrative planes:

- tenant administrators
- tenant operators and approvers
- platform administrators

Platform administration must be rare, auditable, and separate from normal tenant workflow actions.

## Cross-Tenant Behavior

Release 1 should avoid business workflows that span multiple tenants. If a future use case requires cross-tenant coordination, it should be modeled as:

- multiple tenant-local records
- explicit linkage records
- auditable cross-tenant control approvals

It should not be modeled as one shared mutable workflow record.

## Finance-Specific Tenancy Implications

Because Release 1 is centered on finance actions:

- approval thresholds are tenant-specific
- account references in derived finance indexes are tenant-specific or tenant-mapped
- reconciliation and export views should preserve tenant-local business context

## Enforcement Posture

The implementation now enforces tenancy through a combination of:

- authenticated tenant context
- authorization checks on every API and background task
- tenant filtering at the data access layer
- PostgreSQL row-level security on core tenant-scoped workflow tables
- audit logging for privileged access

## PostgreSQL RLS Foundation

PostgreSQL deployments now set explicit session context for authenticated requests:

- `app.current_tenant_scope`
- `app.current_is_platform_admin`
- `app.current_principal_id`

That context is applied at request start after bearer authentication succeeds and is re-applied at the
start of each new transaction. Core tenant-scoped workflow tables use `tenant_id`-based row-level
security policies so the database can reject cross-tenant reads and writes even if an application-layer
filter is missed.

The initial RLS foundation covers the core workflow and artifact tables:

- tenants
- policies
- action_intent_records
- approval_requests
- approver_assignments
- approval_decisions
- evidence_objects
- signing_key_references
- issued_proofs
- signing_operation_records
- escrow_records
- escrow_transition_records
- receipt_records
- reconciliation_records
- audit_events

## Current Limits

This is an incremental hardening step, not a complete multi-tenant isolation model.

- SQLite local and test environments do not enforce PostgreSQL RLS and still rely on application-layer
  checks.
- Auth and admin foundation tables such as `tenant_memberships`, `roles`, and `service_principals` are
  not yet covered by RLS policies in this pass.
- Any future background job or non-request database worker must set session tenant context explicitly
  before touching tenant-scoped rows.
