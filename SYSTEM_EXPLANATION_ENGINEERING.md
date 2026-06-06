# Actenon Cloud Engineering Explanation

## Purpose

Actenon Cloud is the hosted control-plane service above a separate open execution kernel. It uses kernel-aligned contracts for Action Intent intake and receipt ingestion, then adds tenant-scoped governance, workflow control, proof issuance, escrow lifecycle tracking, and audit.

The service is intentionally backend-first and finance-focused.

## Ownership Boundary

### This Repo Owns

- tenant, admin, auth, and service-principal control surfaces
- tenant workflow policy definition and evaluation
- Action Intent intake persistence and idempotency
- approval and evidence workflows
- proof issuance records and signing orchestration
- capability escrow lifecycle records
- receipt storage, indexing, reconciliation hooks, and audit traces

### The Open Kernel Owns

- public Action Intent and receipt contracts
- verifier logic
- execution-side semantics
- canonical low-level execution artifacts

This repo consumes kernel contracts. It must not fork kernel semantics.

## Current Runtime Shape

- single FastAPI service
- SQLAlchemy persistence layer
- Alembic migrations
- structured request logging
- health and readiness endpoints
- development bearer auth with role-based authorization

## Current Major Subsystems

### Access And Tenancy

- `User`
- `Role`
- `TenantMembership`
- `ServicePrincipal`

These entities support platform-level and tenant-level permission checks. Current auth is intentionally limited to development-signed bearer tokens for `local` and `test`.

### Policy And Intake

- `Tenant`
- `Policy`
- `ActionIntentRecord`

The intake path validates against a pinned external kernel Action Intent schema, persists the request, evaluates policy deterministically, and records the initial lifecycle states.

### Approval And Evidence

- `ApprovalRequest`
- `ApproverAssignment`
- `ApprovalDecision`
- `EvidenceObject`

The approval engine supports missing approval, missing evidence, completed approval chains, expiry, and basic separation-of-duties.

### Proof Issuance And Signing

- `SigningKeyReference`
- `SigningOperationRecord`
- `IssuedProof`

Proof issuance binds to exact audience, exact scope, exact Action Intent digest, nonce, and expiry. The implemented signing backend is development-local HMAC. Managed signing backends are modeled, not implemented.

### Escrow And Lifecycle

- `EscrowRecord`
- `EscrowTransitionRecord`

Escrow records bind to an issued proof and track hold, release, consume, revoke, quarantine, and expiry. Current release behavior is honest development simulation, not a real external provider bridge.

### Receipts, Reconciliation, And Audit

- `ReceiptRecord`
- `ReconciliationRecord`
- `AuditEvent`

Receipt ingestion validates against a pinned kernel receipt schema, stores searchable indexes, creates reconciliation hooks, and supports end-to-end trace and export views.

## Current Validation Path

The repo currently validates through:

- `ruff`
- `pytest`
- `alembic upgrade head`
- `bash scripts/verify.sh`
- `bash scripts/judge.sh`

`scripts/verify.sh` is the main acceptance entrypoint and should remain so.

## Honest Maturity Statement

This repo is credible for internal development and early pilot engineering because the main finance control-plane flows are implemented and tested.

It is not yet credible for production deployment because the biggest trust-boundary and operations controls are still missing:

- production identity and SSO
- managed signing infrastructure
- real provider release integrations
- stronger tenant isolation controls
- production observability and deployment hardening
