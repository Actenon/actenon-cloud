# Ship Status

**Last validated:** 2026-07-09

Validation commands: verify.sh, judge.sh, pytest

## Internal Development Readiness

- Lint: **GREEN** (ruff check passes)
- Tests: **GREEN** (125 passed)
- Verify: **GREEN** (422 checks passed)
- Judge: **GREEN** (Overall: PASS)
- Docker build: **GREEN**
- Migrations: **GREEN** (alembic upgrade head, incl. RLS migration)

## Design-Partner Pilot Readiness

- Single-tenant deployment: **READY** (with operator-managed PostgreSQL)
- Invoice payment workflow: **IMPLEMENTED**
- Pilot UI: **FUNCTIONAL** (responsive, mobile-friendly, sticky table headers)
- API: **STABLE** (health, metrics, action intents, approvals, audit)
- Signing: **Ed25519** (key rotation works; KMS required for production)
- Evidence: **LocalFS + commitment layer** (S3 requires deployment)
- Capability release: **REAL** (signed JWT-like tokens, not simulated)
- Auth: **OIDC-ready** (dev bearer refused in production; OIDC verification implemented)
- Tenant isolation: **RLS migration ready** (requires PostgreSQL deployment)
- Observability: **Metrics + OTel + alerts** (collector/scrape require deployment)
- Backup/restore: **TESTED** (hash-chain verify passes after restore)
- CI: **Kernel conformance + security scanning** (SBOM + pip-audit)

## Production Deployment Readiness

**CONDITIONAL.** The code is production-ready conditional on operator-provisioned
infrastructure:

- KMS-backed Ed25519 signing (adapter + boot-refusal in place; needs real KMS endpoint)
- PostgreSQL with RLS enabled (migration ready; needs managed Postgres)
- OIDC identity provider (verification implemented; needs real OIDC issuer)
- Object storage for evidence (LocalFS works; S3 for production)
- OTel collector + Prometheus + alerting pipeline (instrumentation + rules shipped)
- HA/DR/autoscaling (operator topology)

**Production: yes, with operator-provisioned infrastructure.**
