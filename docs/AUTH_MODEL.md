# Auth Model

## Current Scope

This repository implements a real development auth path and one intentional production auth stub for Actenon Cloud. It is intentionally backend-first and intentionally narrow:

- Development-signed bearer authentication is implemented for `local` and `test`.
- `external_managed_bearer` exists as a configuration stub and fails intentionally until managed bearer verification is integrated.
- Operator sessions are backed by `User` plus `TenantMembership` records.
- Service-to-service sessions are backed by `ServicePrincipal` records.
- Authorization is resolved from persisted `Role` definitions at request time.

This is not yet production SSO, production workload identity, or managed federation.

## Auth Modes

### `development_signed_bearer`

- implemented now
- signs the internal `acp1` bearer envelope with `ACTION_CONTROL_PLANE_DEV_SIGNING_SECRET`
- supports local bootstrap and dev token issuance in `local` and `test`

### `external_managed_bearer`

- stubbed now
- intended future mode for enterprise operator bearer auth and managed service bearer auth
- currently fails intentionally during bearer authentication
- currently disables bootstrap and dev token issuance endpoints

This stub is present so the production path is explicit in code and estimable without pretending it is complete.

## Principal Types

- `user`
  Human operator, analyst, approver, or tenant administrator.
- `service_principal`
  Internal or partner automation principal used for controlled API-to-API access.

## Implemented Flows

### Platform Bootstrap

- `POST /api/v1/auth/bootstrap/platform-admin`
- Requires `X-Action-Control-Plane-Bootstrap-Token`.
- Enabled only in `local` and `test`.
- Creates or reuses the first platform administrator and returns a signed bearer token.

### Operator Auth

- `POST /api/v1/auth/dev/operator-token`
- Returns a signed bearer token for an existing `User`.
- Intended for local development, integration tests, and controlled bootstrap only.

### Service Auth

- `POST /api/v1/auth/dev/service-token`
- Returns a signed bearer token for an existing `ServicePrincipal`.
- Used to model internal service-to-service calls such as receipt ingestion and lifecycle updates.

### Session Introspection

- `GET /api/v1/auth/session`
- Returns the resolved principal, platform roles, platform permissions, tenant roles, and tenant permissions for the current bearer token.

## Token Model

- Format: signed bearer token with an internal `acp1` envelope.
- Backing secret: `ACTION_CONTROL_PLANE_DEV_SIGNING_SECRET`
- Principal metadata in token:
  - principal type
  - principal id
  - token kind
  - issued-at
  - expiry
- Effective permissions are not trusted from the token.
- Effective permissions are loaded from the database on each request, which keeps revocation and role changes meaningful.

The `acp1` token format applies only to `development_signed_bearer`. It is not the target production token format.

## Authorization Model

Two scopes exist:

- Platform scope
  - Example permissions: `platform.admin.manage`, `platform.auth.manage`, `platform.tenants.manage`
- Tenant scope
  - Example permissions: `tenant.policy.write`, `tenant.receipt.read`, `tenant.audit.read`

Platform administrators can act across tenants. Non-platform sessions are constrained to tenant memberships or tenant-scoped service principal assignments.

## Current Limitations

- No OIDC or SAML SSO yet.
- No SCIM, lifecycle sync, or JIT provisioning yet.
- No mTLS, SPIFFE, or cloud workload identity integration yet.
- No refresh tokens or browser session model yet.
- `external_managed_bearer` is only a stub right now and will return a clear failure until real managed bearer validation logic is added.
- Some domain request payloads still carry caller-declared actor fields for workflow provenance; binding every one of those fields to the authenticated session is still a follow-on hardening step.

## Managed Bearer Upgrade Path

The production auth seam now lives in `app/services/auth.py`:

- `AuthService.authenticate_bearer_token(...)`
- `AuthService._authenticate_external_managed_bearer(...)`

To complete the managed bearer path, integrate:

- issuer validation against the configured enterprise IdP or workload identity issuer
- audience validation for the Actenon Cloud API
- signature verification through JWKS, workload identity, or equivalent managed key discovery
- principal-to-`User` and principal-to-`ServicePrincipal` resolution using stable external subject identifiers
- clear handling for disabled users, suspended service principals, and tenant membership changes
- audit logging for auth failures, token issuer, key id, and resolved principal

## Production Follow-On

Before production enterprise rollout, replace or augment development bearer auth with:

- enterprise IdP integration for operators
- managed workload identity for services
- secret rotation and key versioning for any remaining bearer signing surfaces
- stronger session revocation and audit coverage
- enforced actor-to-session binding across all mutation APIs
