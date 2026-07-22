# Deployability Audit

## Purpose

This document audits the current codebase for one honest, repeatable managed single-tenant Actenon Cloud pilot deployment.

It is intentionally narrow:

- one hosted environment per design partner
- one invoice payment execution workflow
- one application runtime shape
- no Kubernetes
- no generic platform installer

## Runtime Facts Confirmed In Code

### Application Entrypoint

- The application entrypoint is `app.main:app`.
- The web runtime is a single FastAPI process started with Uvicorn.
- The same process serves:
  - API routes under `ACTION_CONTROL_PLANE_API_V1_PREFIX`
  - the built-in pilot UI routes
  - the pilot UI static assets

### Process Model

- There is no worker tier.
- There is no queue broker.
- There is no background scheduler.
- There is no separate receipt processor, issuance worker, or async task runner in the repo.
- Approval, evidence, issuance, escrow, receipt, and audit flows all execute in request-response paths.

### Database And Migrations

- The runtime uses one SQLAlchemy database URL from `ACTION_CONTROL_PLANE_DATABASE_URL`.
- SQLite is supported for local and test use.
- PostgreSQL is the honest hosted-pilot database path.
- Alembic is real and the repo contains six migration revisions under [migrations/versions](/Users/sarahpounder/AI%20Agent%20Execution%20Control%20Layer/migrations/versions).
- Migrations are not applied automatically during FastAPI startup.
- The container entrypoint exposes:
  - `migrate`
  - `web`
  - `migrate-and-web`

### Evidence Storage

- Uploaded evidence bytes are written to a filesystem-backed store rooted at `ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT`.
- Evidence readiness depends on that path being present and writable.
- Object storage is not a boot dependency for the current runtime.
- Evidence content download is only implemented for filesystem-backed uploads.

### Config And Environment Handling

- Runtime configuration is loaded from process environment through `pydantic-settings`.
- Optional `.env` loading exists for local use.
- The app validates:
  - database URL shape
  - evidence storage path writability
  - secret minimum length
  - environment-specific runtime rules

### Health Surface

- `GET /api/v1/health/live` proves the process is serving HTTP.
- `GET /api/v1/health/ready` checks:
  - database connectivity
  - filesystem-backed evidence storage availability

## Minimum Deployable Runtime

The smallest honest hosted-pilot runtime is:

1. One migration process using the application image.
2. One web process using the same application image.
3. One PostgreSQL database.
4. One mounted persistent writable evidence directory.
5. One reverse proxy or TLS ingress in front of the web process.
6. One secret-injection path for runtime configuration.
7. One centralized log collection path.

That is enough to run the current pilot product surface. Nothing in the code requires Redis, Celery, Kafka, cron workers, or Kubernetes.

## Required Services And Processes

| Component | Required | Why |
| --- | --- | --- |
| Migration invocation | Yes | Applies Alembic revisions before traffic |
| Web runtime | Yes | Serves API and pilot UI |
| PostgreSQL | Yes for hosted pilot | Persistent state for all domain records |
| Persistent evidence mount | Yes | Stores uploaded evidence bytes |
| TLS ingress or reverse proxy | Yes | Keeps TLS termination outside the app process |
| Secret injection | Yes | Supplies DB credentials and pilot secrets |
| Central log collection | Yes | Current observability is log-first |
| Background worker | No | No async task system exists in the repo |
| Queue broker | No | No queue-backed flow exists in the repo |
| Object storage | No for boot | Current evidence write path is filesystem-backed |
| Verifier service | No for boot | Remains external to this repo and runtime |

## Migration And Startup Sequencing

Recommended hosted-pilot sequence:

1. Provision managed PostgreSQL.
2. Provision a persistent writable evidence directory or volume.
3. Inject runtime env vars and non-default secrets.
4. Pull or build the application image.
5. Run `python -m alembic upgrade head` from that image.
6. Start the web process with `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
7. Verify `GET /api/v1/health/live`.
8. Verify `GET /api/v1/health/ready`.
9. Only then perform pilot operator bootstrap or token validation.

`migrate-and-web` exists, but it is not the clearest hosted-pilot default because it couples schema change and serving startup into one process boundary.

## Environment And Secret Categories

### Core Runtime

- `ACTION_CONTROL_PLANE_ENVIRONMENT`
- `ACTION_CONTROL_PLANE_HOST`
- `ACTION_CONTROL_PLANE_PORT`
- `ACTION_CONTROL_PLANE_API_V1_PREFIX`
- `ACTION_CONTROL_PLANE_ENABLE_DOCS`
- `ACTION_CONTROL_PLANE_REQUEST_TIMEOUT_SECONDS`
- `ACTION_CONTROL_PLANE_LOG_LEVEL`
- `ACTION_CONTROL_PLANE_LOG_FORMAT`

### Database

- `ACTION_CONTROL_PLANE_DATABASE_URL`

### Evidence Storage

- `ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT`

### Auth And Bootstrap

- `ACTION_CONTROL_PLANE_AUTH_MODE`
- `ACTION_CONTROL_PLANE_BOOTSTRAP_ADMIN_TOKEN`
- `ACTION_CONTROL_PLANE_AUTH_OPERATOR_TOKEN_TTL_SECONDS`
- `ACTION_CONTROL_PLANE_AUTH_SERVICE_TOKEN_TTL_SECONDS`

### Proof Issuer And Signing

- `ACTION_CONTROL_PLANE_PROOF_ISSUER_NAME`
- `ACTION_CONTROL_PLANE_PROOF_ISSUER_URI`
- `ACTION_CONTROL_PLANE_PROOF_ISSUER_TRUST_TIER`
- `ACTION_CONTROL_PLANE_PROOF_DEFAULT_TTL_SECONDS`
- `ACTION_CONTROL_PLANE_PROOF_MAX_TTL_SECONDS`
- `ACTION_CONTROL_PLANE_DEV_SIGNING_SECRET`

### Capability Release

- `ACTION_CONTROL_PLANE_CAPABILITY_RELEASE_MODE`
- `ACTION_CONTROL_PLANE_CAPABILITY_DEFAULT_TTL_SECONDS`
- `ACTION_CONTROL_PLANE_CAPABILITY_MAX_TTL_SECONDS`

## Biggest Deployment Blockers

### Hosted Auth Bootstrap Is Not Cleanly Packaged Yet

- The hosted pilot env template uses `ACTION_CONTROL_PLANE_ENVIRONMENT=staging`.
- The implemented bootstrap and dev token issuance flows are only enabled in `local` and `test`.
- The service can validate existing bearer tokens in non-local environments, but the repo does not yet provide one clean, staging-safe operator bootstrap flow for a fresh hosted pilot environment.

This is the most important repeatable-deployment blocker in the current repo.

### Pilot Runtime Cannot Honestly Be Labeled `production`

- Production config validation rejects:
  - default signing secret
  - development bearer auth
  - simulated capability release
  - interactive docs
  - SQLite

That is correct and truthful, but it means the honest hosted pilot posture is still `staging-like managed pilot`, not production deployment.

### Evidence Durability Is Filesystem-Bound

- Hosted pilots need mounted persistent storage for evidence uploads.
- The repo does not yet provide a native object-storage upload adapter.
- Backup and restore for evidence remain operator responsibilities outside the app.

### Documentation Drift Still Exists

- [migrations/README.md](/Users/sarahpounder/AI%20Agent%20Execution%20Control%20Layer/migrations/README.md) still says no business migrations exist, which is no longer true.
- [deploy/env/hosted-pilot.env.example](/Users/sarahpounder/AI%20Agent%20Execution%20Control%20Layer/deploy/env/hosted-pilot.env.example) still suggests a hosted profile that does not line up with the current in-repo bootstrap flows.

Those do not break the runtime directly, but they reduce operator confidence and can mislead deployment work.

## Honest Managed-Pilot Claim

Today the repo supports one believable hosted claim:

- one operator-run single-tenant pilot environment
- one web runtime
- one migration step
- one managed PostgreSQL database
- one mounted evidence path
- one external TLS ingress layer

It does not yet support an honest claim of broad hosted product readiness, self-serve deployment, or production-hardened cloud operations.
