# Blockers

## Purpose

This file lists the gaps that prevent Actenon Cloud from being honestly
described as production-ready. Each category is marked CLOSED (with proof),
PARTIAL (with exactly what remains), or REQUIRES DEPLOYMENT (operator action).

## Buyer-Facing Summary

Actenon Cloud is a managed control plane for governed agent execution. It is
credible as a supervised design-partner pilot. It is NOT production-ready.

## Blocker Categories

### B1. Signing And Trust — PARTIAL

**CLOSED:** dev-HMAC signing has been REMOVED. The signing path uses Ed25519
exclusively. Production boot is refused without `ACTENON_KMS_ENDPOINT`.
Tests: `tests/contract/test_signing_ed25519_only.py` (9 tests, all pass).

**REMAINS:**
- KmsEd25519Backend concrete implementation (adapter interface exists; real
  KMS endpoint wiring requires operator-provided infrastructure).
- Key rotation: multiple keys supported but automated rotation + published
  JWKS verification key history not implemented.

### B2. Evidence Durability + PHI — PARTIAL

**CLOSED:** Field-classification layer implemented
(`app/services/field_classification.py`). PHI/PII fields are replaced with
salted commitments in the immutable record. Erasing raw evidence preserves
the hash chain (GDPR Art.17). Tests: `tests/contract/test_field_classification.py`
(5 tests, all pass).

**REMAINS:**
- The commitment layer is not yet wired into the receipt ingestion path
  (`receipts.py` still stores raw `kernel_receipt` in `receipt_payload`).
- ObjectStoreEvidenceStore (S3-compatible) not implemented; LocalFsEvidenceStore
  is the current backend.
- Per-tenant salts not yet generated/stored.

### B3. Money As Float — CLOSED (in permit; cloud uses integer minor units)

**CLOSED:** Permit's budget arithmetic now uses `Decimal` instead of `float`.
F2 proof: 3 × $0.10 against $0.30 = 3 ALLOWs, remaining exactly 0.0.
Cloud already uses `amount_minor: int` in its API layer.

**REMAINS:**
- Currency binding (rejecting JPY action vs USD budget) not yet implemented
  in permit's PDP.

### B4. Capability Release — REQUIRES DEPLOYMENT

The simulated capability-release path is still in place. Replacing it with
permit's real broker requires adding `actenon-permit` as a cloud runtime
dependency and changing the escrow service architecture. This is a
production-hardening item, not a code fix.

### B5. Tenant Isolation — REQUIRES DEPLOYMENT

Postgres row-level security (RLS) requires a managed PostgreSQL instance
and Alembic migration. The schema is designed for RLS but the migration
is not implemented. Per-tenant key separation depends on B2 per-tenant
salts.

### B6. Identity And Access — PARTIAL

**CLOSED:** Production boot is refused if `development_signed_bearer` auth
mode is enabled. The `external_managed_bearer` mode is available.

**REMAINS:**
- OIDC/SAML operator SSO not implemented.
- Service-to-service workload tokens not implemented.
- Bootstrap admin backdoor still exists (must be removed for production).

### B7. Kernel Compatibility CI — PARTIAL

**CLOSED:** Cloud imports `FailureCode` from the kernel (single source of
truth). Cross-repo conformance tests exist in permit
(`tests/test_cross_repo_conformance.py`).

**REMAINS:**
- CI job that pulls kernel conformance vectors and runs them against cloud
  is not yet wired.
- Nightly live-compat workflow not implemented.

### B8. Release Governance — REQUIRES DEPLOYMENT

Signed artifact publication (cosign), SBOM generation, dependency-vulnerability
gate, and build provenance are all deployment/CI infrastructure items.

### B9. Observability — PARTIAL

**CLOSED:** `/metrics` endpoint exposes Prometheus-format metrics with
correct path templates (including dynamic routes). Health/readiness endpoints
work. Structured log correlation IDs are present.

**REMAINS:**
- OpenTelemetry tracing not implemented.
- Alert rule set (YAML) not shipped.
- RED/USE metrics for the decision path not fully covered.

### B10. Deployment/Recovery — REQUIRES DEPLOYMENT

HA topology, autoscaling, multi-region DR, paging/on-call rotation, and
incident response ownership are operator responsibilities. The repo provides
Dockerfile, docker-compose, and migration tooling. Automated rollback and
exercised restore are not implemented.
