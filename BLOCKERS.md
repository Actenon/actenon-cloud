# Blockers

## Purpose

This file lists the gaps that prevent Actenon Cloud from being honestly
described as production-ready. Each category is marked CLOSED (with proof),
PARTIAL (with exactly what remains), or REQUIRES DEPLOYMENT (operator action).

## Buyer-Facing Summary

Actenon Cloud is a managed control plane for governed agent execution. It is
credible as a supervised design-partner pilot. It is NOT production-ready
without operator-provisioned infrastructure (KMS, PostgreSQL with RLS, OIDC
provider, object storage, alerting pipeline).

## Blocker Categories

### B1. Signing And Trust — CLOSED

dev-HMAC signing has been REMOVED. The signing path uses Ed25519 exclusively.
Production boot is refused without `ACTENON_KMS_ENDPOINT`. Key rotation works:
new proofs use the new key_id; proofs signed with old key_ids still verify.
Published JWKS-style verification key set contains all known keys.
Tests: `tests/contract/test_signing_ed25519_only.py` (9 tests),
`tests/contract/test_key_rotation.py` (3 tests) — all pass.

**REQUIRES DEPLOYMENT:** KmsEd25519Backend concrete implementation needs a
real KMS endpoint (AWS KMS, GCP KMS, or HSM). The adapter interface and
boot-refusal guard are in place.

### B2. Evidence Durability + PHI — PARTIAL

Field-classification layer implemented (`app/services/field_classification.py`).
PHI/PII fields are replaced with salted commitments in the immutable record.
Erasing raw evidence preserves the hash chain (GDPR Art.17).
Tests: `tests/contract/test_field_classification.py` (5 tests) — all pass.

**REMAINS:**
- The commitment layer is not yet wired into the receipt ingestion path.
- ObjectStoreEvidenceStore (S3) not implemented; LocalFsEvidenceStore is current.
- Per-tenant salts not yet generated/stored.

### B3. Money As Float — CLOSED

Permit's budget arithmetic uses `Decimal`. Cloud uses `amount_minor: int`.
F2 proof: 3 × $0.10 against $0.30 = 3 ALLOWs, remaining exactly 0.0.

### B4. Capability Release — CLOSED

The simulated capability-release path has been REPLACED with a real signed
capability token. The token is a JWT-like structure signed via the Ed25519
signer. `"simulated": False` in release metadata.
Tests: `tests/contract/test_broker_release.py` (4 tests) — all pass.

### B5. Tenant Isolation — PARTIAL

Alembic migration `20260709_0012_tenant_rls.py` enables Postgres RLS on all
10 tenant-scoped tables with USING + WITH CHECK policies. Session-bound actors:
`requested_by` is overridden from the authenticated session, not client-supplied.

**REQUIRES DEPLOYMENT:** RLS policies require a managed PostgreSQL instance
(with `SET LOCAL app.tenant_id`). SQLite is a safe no-op for dev/test.

### B6. Identity And Access — PARTIAL

Production boot is refused with `development_signed_bearer` auth mode.
OIDC token verification implemented (`AuthService.verify_oidc_token`) with
JWKS caching. Production requires `oidc_issuer_url`.
Dev bearer path is refused in production even if config is bypassed.
Tests: `tests/contract/test_identity.py` (9 tests) — all pass.

**REMAINS:**
- OIDC provider integration not tested end-to-end (requires real OIDC issuer).
- Bootstrap admin backdoor still exists (refused in production by config guard).

### B7. Kernel Compatibility CI — CLOSED

CI job `.github/workflows/kernel-conformance.yml` runs contract tests +
kernel conformance on every push/PR and nightly at 3 AM UTC.

### B8. Release Governance — CLOSED

CI job `.github/workflows/security.yml` runs pip-audit (fails on HIGH/CRITICAL),
generates CycloneDX SBOM, and runs weekly. SBOM uploaded as build artifact.

### B9. Observability — PARTIAL

`/metrics` endpoint exposes Prometheus-format metrics with correct path
templates. Health/readiness endpoints work. Structured log correlation IDs
present. OpenTelemetry tracing instrumentation added (optional, guarded by
import). Alert rules shipped in `config/alerts.yml`.

**REQUIRES DEPLOYMENT:** OTel collector, Prometheus scrape config, and
alerting pipeline must be provisioned by the operator.

### B10. Deployment/Recovery — PARTIAL

Backup → destroy → restore → hash-chain verify() test passes
(`tests/integration/test_backup_restore.py`). Dockerfile, docker-compose,
and migration tooling are in place.

**REQUIRES DEPLOYMENT:** HA topology, autoscaling, multi-region DR,
paging/on-call rotation, and incident response ownership are operator
responsibilities. Automated rollback in CI not yet implemented.
