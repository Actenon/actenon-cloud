# Containerized Deployment

## Purpose

This document defines the minimum repeatable containerized deployment path for Actenon Cloud in a managed single-tenant invoice payment pilot.

It is intentionally narrow:

- one application image
- one migration command from the same image
- one PostgreSQL service for reproducible local stack testing
- one mounted persistent evidence volume
- no worker tier

This is not a Kubernetes guide and not a broad self-serve platform installer.

## Artifacts

- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `.env.compose.example`
- `scripts/container-entrypoint.sh`

## What The Stack Runs

### `app`

Runs the FastAPI service and built-in pilot UI.

### `migrate`

Runs `alembic upgrade head` from the same application image.

### `db`

Runs PostgreSQL for local and reproducible pilot-stack testing. For a hosted pilot, this service should usually be replaced by managed PostgreSQL rather than containerized in the customer environment.

## Profile Reality

The compose example is intentionally a `local` runtime profile.

That is deliberate:

- it keeps the current repo-native bootstrap and dev token issuance flows available
- it supports repeatable local and protected pilot-stack smoke testing
- it does not overclaim hosted-production readiness

For a managed hosted pilot environment template, use:

- `deploy/env/hosted-pilot.env.example`

## First-Time Setup

1. Copy the compose environment file:

```bash
cp .env.compose.example .env.compose
```

2. Replace the placeholder secrets in `.env.compose`.

3. Build the image:

```bash
make container-build
```

## Start The Stack

Start the database, run migrations, then start the app:

```bash
make container-up
```

If you want to run the steps separately:

```bash
make container-db-up
make container-migrate
docker compose --env-file .env.compose up -d app
```

The service will be available at:

- `http://127.0.0.1:8000/pilot/actions`
- `http://127.0.0.1:8000/api/v1/health/live`
- `http://127.0.0.1:8000/api/v1/health/ready`

## Operational Commands

Show rendered compose config:

```bash
make container-config
```

Run migrations again after schema changes:

```bash
make container-migrate
```

Verify the running stack:

```bash
make container-verify
```

View logs:

```bash
make container-logs
```

List running services:

```bash
make container-ps
```

Stop the stack:

```bash
make container-down
```

The compose stack uses one named PostgreSQL volume and one named evidence volume so repeated local starts do not lose runtime state by default.

## Verification

After the stack starts:

```bash
make container-verify
```

Equivalent direct checks:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health/live
curl -fsS http://127.0.0.1:8000/api/v1/health/ready
```

The application container also exposes a readiness healthcheck, and the compose `app` service mirrors that healthcheck.

## First-Run Access

Because the compose example uses the `local` runtime profile, the repo-native bootstrap flow remains available for first-run bring-up.

If you need a first operator session in the compose stack, use the local bootstrap flow documented in:

- `docs/LOCAL_DEV_SETUP.md`

## Hosted Pilot Adaptation

For a managed pilot deployment, keep the same application image and startup commands but replace the local `db` service with managed PostgreSQL. Keep the mounted evidence path or equivalent persistent writable storage available inside the container runtime.

The separate verifier remains outside this stack as an external dependency or interface.

Supporting hosted-pilot artifacts:

- `deploy/env/hosted-pilot.env.example`
- `deploy/nginx/action-control-plane.conf`
- `DATABASE_AND_MIGRATIONS.md`
- `TLS_SETUP.md`

## Current Limits

- There is still no worker tier.
- Readiness checks the database and filesystem-backed evidence storage.
- Evidence uploads are filesystem-backed today.
- The hosted pilot env template still needs an explicit operator bootstrap strategy outside this compose profile.
- Auth, signing, and capability release remain pilot-stage rather than production-grade.
