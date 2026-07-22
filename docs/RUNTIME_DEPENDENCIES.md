# Runtime Dependencies

## Purpose

This document lists the runtime dependencies required to operate the current Actenon Cloud backend in one managed single-tenant pilot form.

It describes what the runtime actually depends on today, not a broader future platform target.

## In-Process Runtime Dependencies

The application image currently depends on:

- Python 3.12
- FastAPI and Uvicorn for the web runtime
- SQLAlchemy for database access
- Alembic for migrations
- Pydantic settings for environment-backed configuration
- `python-multipart` for evidence upload handling
- `jsonschema` for contract validation

## External Service Dependencies

### Required

| Dependency | Why It Is Required | Current Support |
| --- | --- | --- |
| PostgreSQL-compatible database | Persistent state for tenants, policies, actions, approvals, evidence metadata, proofs, escrow, receipts, and audit | Supported through `ACTION_CONTROL_PLANE_DATABASE_URL` |
| Writable persistent filesystem path | Stores uploaded evidence bytes | Supported through `ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT` |
| TLS ingress or reverse proxy | Terminates TLS and fronts the web service | External to the app |
| Secret injection mechanism | Supplies non-default pilot secrets and connection strings | External to the app |
| Central log collection | Makes structured logs usable in pilot operations | External to the app |

Object storage is not a required runtime dependency for the current application process. If used in a hosted pilot, it should be treated as an adjacent operational dependency for backup, export, or later hardening.

### Recommended For Pilot Operations

| Dependency | Why It Helps | Current Support |
| --- | --- | --- |
| Database backups | Reduces pilot data loss risk | External operational control |
| Volume snapshots or file backup for evidence | Protects uploaded evidence artifacts | External operational control |
| Basic uptime and readiness checks | Detects obvious service failures | Supported through health endpoints |

## External Interfaces And Dependencies

### Separate Open Kernel

The control plane depends on kernel-published contracts and execution-side artifact semantics from a separate open kernel repo. Those contracts are consumed here; they are not owned here.

### Separate External Verifier

Proof verification remains a dependency on a separate verifier repo or verifier interface. This repo issues and tracks proofs, but does not implement verifier logic.

## Explicit Non-Dependencies Today

The current hosted pilot path does not require:

- Redis
- Celery
- RQ
- Kafka
- RabbitMQ
- cron workers
- background schedulers
- Elasticsearch or OpenSearch
- managed object storage adapters
- managed signing backends

Those may become useful later, but they are not runtime requirements for the current single-tenant pilot deployment form.

## Configuration And Secret Classes

### Connection Configuration

- database URL
- host and port
- API prefix

### Storage Configuration

- evidence upload backend selection
- evidence storage root
- optional object-store bucket, prefix, and endpoint for the future backend path

### Trust And Issuer Configuration

- issuer name
- issuer URI
- issuer trust tier
- proof TTL settings

### Secrets

- development signing secret
- bootstrap admin token

### Auth Configuration

- auth mode
- operator token TTL
- service token TTL

### Capability Release Configuration

- capability release mode
- capability TTL settings

## Runtime Gaps That Matter Operationally

- Evidence uploads are filesystem-backed, not object-store-backed.
- Readiness now checks both database connectivity and evidence storage availability.
- Metrics and tracing exporters are not implemented.
- Auth, signing, and capability release remain pilot-stage rather than production-grade.
- The object-store backend path is now explicit in configuration and code, but live object-store upload and retrieval are not implemented in this repo build.

## Minimum Dependency Set For The Pilot

The smallest honest dependency set for a hosted pilot is:

1. one application container
2. one migration invocation using the same image
3. one PostgreSQL instance
4. one mounted persistent evidence directory
5. one ingress path with TLS
6. one log collection path

For local reproducibility, `docker-compose.yml` also includes a `db` service. For a hosted pilot, that same dependency should usually be satisfied with managed PostgreSQL instead.
