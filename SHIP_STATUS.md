# Ship Status

**Last validated:** 2026-07-09

Validation commands: verify.sh, judge.sh, pytest

## Internal Development Readiness

- Lint: **GREEN** (ruff check passes)
- Tests: **GREEN** (108 passed)
- Verify: **GREEN** (422 checks passed)
- Judge: **GREEN** (Overall: PASS)
- Docker build: **GREEN**
- Migrations: **GREEN** (alembic upgrade head)

## Design-Partner Pilot Readiness

- Single-tenant deployment: **READY** (with operator-managed PostgreSQL)
- Invoice payment workflow: **IMPLEMENTED**
- Pilot UI: **FUNCTIONAL** (responsive, mobile-friendly)
- API: **STABLE** (health, metrics, action intents, approvals, audit)
- Signing: **Ed25519** (dev-local key file; KMS required for production)
- Evidence: **LocalFS** (object store requires deployment)
- Capability release: **SIMULATED** (permit broker integration not yet wired)
- Auth: **Dev bearer** (OIDC SSO not yet implemented)

## Production Deployment Readiness

**NOT READY.** The following blockers remain (see BLOCKERS.md):

- KMS-backed signing (adapter exists, concrete KMS client not wired)
- OIDC/SAML SSO (not implemented)
- Postgres RLS (migration not implemented)
- Real capability release (permit broker not wired)
- Object store evidence (S3 backend not implemented)
- OTel tracing (not implemented)
- Automated rollback/restore (not exercised)
- Signed artifacts + SBOM (CI infrastructure not provisioned)

**Production: no.**
