# Service Identity Plan

## Purpose

This document defines the path from the current service principal model to real service-to-service identity.

## What Exists Today

- `ServicePrincipal` records exist and are permission-scoped.
- The auth service can issue development-signed bearer tokens for service principals.
- Tenant-scoped authorization checks use persisted roles and memberships.
- Audit records can attribute some actions to service principals.

## What Is Simulated Today

- service tokens are issued from the application itself
- no external identity provider is involved
- no workload identity federation is implemented
- no automated secret rotation or token exchange is implemented

## Design-Partner Pilot Requirements

- keep service principal creation restricted to platform admins
- use short-lived service tokens with non-default secrets
- separate pilot service principals by tenant and function
- record issuer, subject, tenant, and role bindings for each token
- prohibit long-lived shared operator tokens for machine automation

## What Must Change For Production

- replace self-issued service tokens with workload identity or external token exchange
- bind service identity to deployment infrastructure instead of static shared secrets
- add issuer validation, audience restrictions, and key rotation outside the app process
- tighten mutation paths so actor identity always comes from the authenticated session, not request payload fields
- support revocation, rotation, and break-glass handling without editing code

## Real Production Target

- external workload identity
- short-lived credentials
- tenant-aware least privilege
- auditable token issuance and revocation
- no long-lived bootstrap path in normal operations
