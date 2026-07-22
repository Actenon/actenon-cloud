# Hosting And Deployment Status

## Purpose

This document states the current deployment reality for Actenon Cloud and distinguishes the managed pilot posture from production-grade cloud readiness.

## Current Deployment Reality

Actenon Cloud currently supports three practical deployment shapes:

1. Local development: one Python API process, SQLite, and filesystem-backed evidence under `./var/evidence`.
2. Reproducible pilot-stack testing: one application image, one migration command from the same image, and one PostgreSQL service via `docker-compose`.
3. Managed design-partner pilot: one dedicated single-tenant environment run by an operator team using the documented app image, managed PostgreSQL, mounted persistent evidence storage, TLS ingress, and centralized log collection.

The third shape is the honest hosted claim today. It is an operator-managed pilot deployment model, not a self-serve hosted product.

## Truth By Hosting Surface

| Surface | Implemented now | Honest statement | Not yet claimable |
| --- | --- | --- | --- |
| Application runtime | Single-process FastAPI service with built-in pilot UI. | The app can be deployed as one runtime plus one migration step. | No worker tier, no queue, no horizontally scaled runtime story. |
| Database | SQLite locally, PostgreSQL in the containerized stack and managed-pilot guidance. | Managed PostgreSQL is the intended path for a hosted pilot. | No HA database posture or exercised disaster recovery workflow is documented in code. |
| Evidence storage | Uploads write to a filesystem-backed path and readiness checks that path. | Hosted pilots need mounted persistent writable storage for live evidence uploads. | No native object-store upload adapter exists in the runtime today. |
| Ingress | Reverse-proxy and TLS artifacts are documented for pilot use. | TLS termination outside the app process is expected in managed deployment. | No production ingress automation, certificate lifecycle automation, or broad platform templates. |
| Operations | Health endpoints and structured logs exist. | A named operator team can supervise a pilot using log collection and health checks. | No alerting backend, no tracing, no metrics pipeline, and no zero-touch operations posture. |
| Provisioning | Environment examples and deployment docs exist. | A capable team can stand up a dedicated pilot environment deliberately. | No self-serve tenant provisioning, no multi-tenant hosted control plane, and no automated environment creation flow. |

## What Makes It Suitable For A Managed Pilot

The current deployment shape is acceptable for a managed pilot because it is intentionally narrow:

- one design partner per environment
- one bounded invoice payment workflow
- explicit operator ownership
- external verifier boundary preserved
- manual but documented deployment steps
- clear acknowledgement that storage, signing, auth, and observability are still early

This is the posture of a supervised managed service engagement, not a generally available cloud platform.

## What It Does Not Mean

The existence of deployment docs, topology diagrams, and environment examples does not mean:

- self-serve cloud onboarding exists
- production automation exists
- the service has HA or multi-region behavior
- restore and rollback have been fully exercised
- the repo is ready for broad external hosting claims

## Recommended Language

Use language like:

- "managed single-tenant pilot deployment"
- "operator-run design-partner environment"
- "pilot-stage hosted setup with explicit operational support"

Avoid language like:

- "production cloud platform"
- "self-serve SaaS"
- "multi-tenant hosted control plane"
- "production-hardened deployment"

## Supporting Docs

- [docs/CONTAINERIZED_DEPLOYMENT.md](docs/CONTAINERIZED_DEPLOYMENT.md)
- [HOSTED_PILOT_TOPOLOGY.md](HOSTED_PILOT_TOPOLOGY.md)
- [DATABASE_AND_MIGRATIONS.md](DATABASE_AND_MIGRATIONS.md)
- [TLS_SETUP.md](TLS_SETUP.md)
- [LOGGING_COLLECTION.md](LOGGING_COLLECTION.md)
- [BACKUP_RESTORE_ASSUMPTIONS.md](BACKUP_RESTORE_ASSUMPTIONS.md)
