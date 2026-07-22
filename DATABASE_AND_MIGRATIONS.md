# Database And Migrations

## Purpose

This document defines the minimum database and migration model for a managed single-tenant invoice payment pilot.

## Database Requirement

Use managed PostgreSQL for the hosted pilot.

Do not use SQLite for hosted pilot operation.

## Connection Model

The application runtime reads one SQLAlchemy database URL:

```text
ACTION_CONTROL_PLANE_DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
```

The hosted pilot environment template is provided in:

- `deploy/env/hosted-pilot.env.example`

## Migration Boundary

The runtime uses the same application image for:

- database migration
- web service startup

The migration command is:

```bash
python -m alembic upgrade head
```

The container entrypoint also supports:

- `migrate`
- `web`
- `migrate-and-web`

## Minimum Hosted Deployment Sequence

1. Confirm the target database is the intended pilot database.
2. Confirm a pre-migration backup or snapshot exists.
3. Run `alembic upgrade head` from the deployment image.
4. Start the web runtime only after migration succeeds.
5. Verify `/api/v1/health/ready`.

## Local Versus Hosted

- `docker-compose.yml` includes PostgreSQL for reproducible local stack use.
- hosted pilot deployments should replace that local database container with managed PostgreSQL.

## Rollback Reality

- migration rollback is still an operator-managed decision
- this repo does not provide automated schema rollback tooling
- database restore depends on the managed database backup capability chosen for the pilot

## Supporting Docs

- `RELEASE_DEPLOY_RUNBOOK.md`
- `DEPLOYMENT_VERIFICATION.md`
- `docs/CONTAINERIZED_DEPLOYMENT.md`
