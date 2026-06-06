# Runtime Overview

## Purpose

This document describes the current backend runtime shape for Actenon Cloud. The service has moved beyond a skeleton: it now includes the finance-focused control-plane APIs, persistence model, auth foundation, and acceptance harness needed for internal development and design-partner preparation.

## Current Runtime Shape

The runtime uses a single Python API service with:

- a FastAPI application entrypoint
- typed environment-backed configuration
- structured logging with request, correlation, and trace identifiers
- an honest observability profile plus an in-process `/metrics` endpoint for hosted pilot operations
- a lightweight application container for runtime wiring
- SQLAlchemy engine and session scaffolding
- Alembic migration scaffolding
- persisted domain models for tenancy, policy, approvals, evidence, issuance, escrow, receipts, and audit
- development bearer auth with platform and tenant permission enforcement
- pytest-based test scaffolding

The current implementation is still intentionally single-process and backend-first. There is now a narrow built-in pilot UI for invoice payment list and detail views, but there is still no broad admin UI, async worker tier, or provider integration mesh.

## Module Overview

| Path | Responsibility |
| --- | --- |
| `app/main.py` | Application entrypoint, startup lifespan, middleware, and router registration |
| `app/config.py` | Environment-backed settings and validation rules |
| `app/logging.py` | Structured log formatting and request-scoped correlation context management |
| `app/telemetry.py` | Honest observability profile describing current logging, metrics, tracing, and readiness boundaries |
| `app/database.py` | Engine creation, session factory, and DB health checks |
| `app/container.py` | Runtime dependency container and startup or shutdown wiring |
| `app/api/` | API routers for health, auth, admin, finance control-plane workflows, and audit |
| `app/pilot_ui/` | Narrow built-in pilot UI for invoice payment queue and action detail views |
| `app/models/` | Persistence models for access control, issuance, escrow, receipts, and audit |
| `app/services/` | Domain services for policy, intake, approvals, evidence, issuance, escrow, receipts, audit, and auth |
| `migrations/` | Alembic environment and revision templates |

## Startup Flow

1. Settings load from process environment and optional `.env`.
2. Runtime validation checks the environment profile and database settings.
3. Logging is configured before the application begins serving traffic.
4. The application container records the current observability profile during startup.
5. The application container creates the database engine and session factory during startup.
6. Routers are mounted under `/api/v1`.
7. Request middleware emits structured completion or failure logs and attaches `X-Request-ID`, `X-Correlation-ID`, and `X-Trace-ID`.
8. Protected routes resolve bearer sessions from persisted roles and memberships.

## Health Surfaces

Implemented route families:

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /metrics`
- `POST /api/v1/auth/bootstrap/platform-admin`
- `GET /api/v1/auth/session`
- `POST /api/v1/admin/...`
- `POST /api/v1/tenants`
- `POST /api/v1/policies`
- `POST /api/v1/action-intents`
- `POST /api/v1/approvals/.../decisions`
- `POST /api/v1/evidence/register`
- `POST /api/v1/evidence/upload`
- `POST /api/v1/issuance/proofs`
- `POST /api/v1/escrow/holds`
- `POST /api/v1/receipts`
- `GET /api/v1/audit/traces/{action_intent_record_id}`

`live` proves the process is serving. `ready` now checks both database connectivity and filesystem-backed evidence storage availability.

`/metrics` exposes an in-process Prometheus text surface for request, dependency, and workflow counters. It is suitable for managed pilot diagnosis, not for claiming a full metrics platform.

## Database Foundation

The runtime uses SQLAlchemy 2.x for:

- tenant and access-control tables
- policy and Action Intent tables
- approval and evidence tables
- signing, proof, and escrow tables
- receipt, reconciliation, and audit tables

Local development defaults to SQLite to keep the boot path small. Production validation rejects SQLite to avoid accidental long-term dependence on it.

## Migration Foundation

Alembic is wired with:

- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/`

The repo currently carries concrete revisions through the enterprise auth foundation. The migration path is real, even though the production datastore choice is still intentionally open.

## Testing Foundation

The current automated test surface covers:

- configuration validation
- liveness and readiness endpoint behavior
- policy management and Action Intent intake
- approvals and evidence lifecycle behavior
- proof issuance and signing behavior
- escrow lifecycle behavior
- receipt ingestion, reconciliation, and audit traces
- tenancy and access-control enforcement

This is still not exhaustive, but it is a real end-to-end service validation path rather than a scaffold-only smoke test.

## Deliberate Limits

This runtime does not yet include:

- enterprise SSO or production workload identity
- managed KMS or HSM-backed signing
- real external capability release integrations
- async job processing
- a managed object storage adapter for evidence uploads; current uploads are filesystem-backed
- metrics exporters, distributed tracing, or alerting backends
- production deployment automation, exercised runbooks, and advanced release controls
- automated synchronization with a live kernel repo artifact feed

Those remain the main production-hardening gaps.
