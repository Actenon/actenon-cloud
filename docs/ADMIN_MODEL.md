# Admin Model

## Current Scope

The implemented admin model is API-first and supports the minimum enterprise control-plane foundation:

- users
- roles
- tenant memberships
- service principals

The current admin layer is meant to support backend workflows and testable access-control behavior. It is not yet a full operator console.

## Core Admin Entities

### User

- Human operator identity record.
- Carries platform-scoped role assignments.
- Can also receive tenant-scoped access through `TenantMembership`.

### Role

- Permission bundle resolved at request time.
- `scope=platform` for global administration.
- `scope=tenant` for tenant-local administration and workflow access.
- System roles are seeded on demand by the auth service.

### TenantMembership

- Binds a `User` to one tenant.
- Carries tenant-scoped role ids.
- This is the primary operator-to-tenant access mapping.

### ServicePrincipal

- Models API-to-API callers.
- Can be platform-scoped or tenant-scoped.
- Current Release 1 use case is tenant-scoped finance automation such as receipt ingestion and lifecycle hooks.

## Implemented System Roles

- `platform_admin`
- `tenant_admin`
- `policy_admin`
- `audit_viewer`
- `service_operator`

These roles are intentionally small and finance-oriented. More specialized approval, reconciliation, and export roles can be added later.

## Implemented Admin APIs

- `POST /api/v1/admin/users`
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/roles`
- `GET /api/v1/admin/roles`
- `POST /api/v1/admin/tenants/{tenant_id}/memberships`
- `GET /api/v1/admin/tenants/{tenant_id}/memberships`
- `POST /api/v1/admin/service-principals`
- `GET /api/v1/admin/service-principals`

## Access Control Rules

- Platform user and platform role management requires `platform.auth.manage`.
- Tenant membership management requires `tenant.membership.manage` for the target tenant.
- Platform administrators implicitly satisfy tenant-level checks.
- Tenant admins can manage tenant-local roles, memberships, and tenant-scoped service principals for their own tenant.

## Scope Boundary

This admin layer manages control-plane access, not business approval chains. Approval requests and approver decisions remain domain workflow objects and are separate from platform administration.

## Intentionally Deferred

- Rich user profile management
- Self-service invitations
- SCIM provisioning
- Role-assignment history UI
- Delegated admin workflows
- Break-glass and emergency access flows
- Cross-tenant enterprise organization model above `Tenant`
