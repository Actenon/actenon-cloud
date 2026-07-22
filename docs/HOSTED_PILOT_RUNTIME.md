# Hosted Pilot Runtime

## Purpose

Define the minimum runtime shape for one managed single-tenant Actenon Cloud pilot deployment.

This document describes what the repo can honestly support now for invoice payment execution. It does not describe a general hosted platform.

## Minimum Runtime Shape

One hosted pilot environment should contain:

1. One Actenon Cloud web runtime.
2. One one-off migration invocation from the same image.
3. One managed PostgreSQL database.
4. One mounted persistent evidence storage path.
5. One TLS ingress or reverse proxy in front of the web runtime.
6. One centralized log collection path.

That is the smallest complete hosted shape supported by the current repo.

## Required Services And Processes

| Service or process | Required | Notes |
| --- | --- | --- |
| Web process | Yes | Runs `app.main:app` and serves API plus pilot UI |
| Migration process | Yes | Runs `alembic upgrade head` before traffic |
| PostgreSQL | Yes | Use managed PostgreSQL for hosted pilot |
| Evidence filesystem path | Yes | Must be writable and persistent |
| TLS ingress | Yes | Keep TLS termination outside the app process |
| Log collection | Yes | Current observability is structured-log-first |
| Worker process | No | No async worker tier exists |
| Scheduler or cron service | No | No scheduled runtime duties exist in repo |
| Queue broker | No | No queue-backed tasks exist |

## Runtime Ports And Paths

### Web Process

- binds to `ACTION_CONTROL_PLANE_HOST`
- listens on `ACTION_CONTROL_PLANE_PORT`
- default internal port is `8000`

### Main HTTP Surfaces

- `/pilot/actions`
- `/pilot/review`
- `/pilot/actions/{action_intent_record_id}`
- `/api/v1/health/live`
- `/api/v1/health/ready`

### Required Persistent Path

- `ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT`

The current runtime writes uploaded evidence into that filesystem root and checks it during readiness.

## Startup Sequence

1. Confirm PostgreSQL is reachable.
2. Confirm the evidence path exists and is writable by the runtime user.
3. Inject the runtime env vars and secrets.
4. Run migrations.
5. Start the web runtime.
6. Verify liveness.
7. Verify readiness.
8. Verify pilot UI and one authenticated action trace path.

Recommended commands:

```bash
python -m alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment Profile Reality

The honest hosted pilot posture is still `staging-like managed pilot`, not production.

Important constraint from the current settings model:

- `production` mode is intentionally rejected while:
  - development bearer auth remains configured
  - development-local signing remains configured
  - simulated capability release remains configured

That means a hosted pilot should not be described as production runtime maturity.

## Secret And Env Categories

### Required To Boot

- database URL
- evidence storage root
- environment
- host and port
- API prefix
- log level and log format
- auth mode
- bootstrap admin token
- dev signing secret
- proof issuer identity fields
- proof TTL fields
- capability release mode
- capability TTL fields

### Operator-Owned Deployment Metadata

These are useful for hosted deployment coordination, but are not consumed directly by the app today:

- public hostname
- TLS cert and key locations
- object-storage backup target
- log collection target
- backup policy label

## Health And Readiness

### Liveness

`GET /api/v1/health/live`

Confirms the process is serving.

### Readiness

`GET /api/v1/health/ready`

Confirms:

- database connectivity
- evidence storage availability

The current readiness surface does not check:

- ingress reachability
- backup posture
- external verifier reachability
- external payment provider health

## Auth Bootstrap Reality

This is the biggest runtime workflow gap for a hosted pilot.

Current code truth:

- authentication of existing bearer tokens works outside local and test
- bootstrap platform-admin issuance is only enabled in `local` and `test`
- dev operator and service token issuance are only enabled in `local` and `test`

Practical implication:

- the repo does not yet provide one clean, staging-safe bring-up flow for creating the first hosted pilot operator session inside the running environment

Until that is addressed, hosted pilot deployment is only partially repeatable end to end from repo-native procedures.

## Evidence Storage Reality

- live evidence uploads are filesystem-backed
- the hosted pilot needs mounted persistent storage for evidence bytes
- object storage may still be used operationally for backup or copy-out, but it is not the native write path today

## External Dependencies That Stay Outside This Runtime

### Separate Kernel

The runtime issues and consumes kernel-aligned artifacts, but the kernel remains a separate repo and dependency.

### Separate Verifier

Proof verification remains outside this repo. The hosted pilot runtime does not need to embed verifier logic.

## What Makes This Runtime Suitable For A Managed Pilot

- single tenant
- one bounded invoice payment workflow
- explicit operator ownership
- explicit migration step
- health endpoints
- structured logs
- built-in pilot UI for queue, review, and trace inspection

## What It Is Not Yet

- production-grade hosted SaaS
- self-serve deployment
- horizontally scaled runtime
- enterprise auth runtime
- managed-signing runtime
- object-storage-native evidence runtime
- automated backup and restore runtime

## Recommended Near-Term Hardening Order

1. Close the hosted auth bootstrap gap.
2. Lock a single canonical hosted image publish path.
3. Formalize backup and restore for PostgreSQL plus evidence files.
4. Add stronger operational checks around the hosted pilot boundary.
