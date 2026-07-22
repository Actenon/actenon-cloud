# Local Development Setup

## Purpose

This document explains how to install, run, test, and validate the current Actenon Cloud service locally.

## Prerequisites

- Python 3.12 or newer
- `make`

## Initial Setup

1. Create a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

2. Copy the environment template:

```bash
cp .env.example .env
```

3. Install the project and dev dependencies:

```bash
make install
```

## Running The Service

Apply migrations before starting the API:

```bash
make migrate-up
```

Start the API locally with autoreload:

```bash
make run
```

The default local service URL is `http://127.0.0.1:8000`.

Current route families:

- `http://127.0.0.1:8000/api/v1/health/live`
- `http://127.0.0.1:8000/api/v1/health/ready`
- `http://127.0.0.1:8000/api/v1/auth/*`
- `http://127.0.0.1:8000/api/v1/admin/*`
- `http://127.0.0.1:8000/api/v1/tenants/*`
- `http://127.0.0.1:8000/api/v1/policies/*`
- `http://127.0.0.1:8000/api/v1/action-intents/*`
- `http://127.0.0.1:8000/api/v1/approvals/*`
- `http://127.0.0.1:8000/api/v1/evidence/*`
- `http://127.0.0.1:8000/api/v1/issuance/*`
- `http://127.0.0.1:8000/api/v1/escrow/*`
- `http://127.0.0.1:8000/api/v1/receipts/*`
- `http://127.0.0.1:8000/api/v1/audit/*`

## Local Auth Bootstrap

In `local` and `test`, the repo implements a development bearer-token flow for bootstrapping.

1. Start the service.
2. Call `POST /api/v1/auth/bootstrap/platform-admin` with the bootstrap token from `.env`.
3. Use the returned bearer token for subsequent admin and tenant-scoped requests.

Example bootstrap request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/bootstrap/platform-admin \
  -H "Content-Type: application/json" \
  -H "X-Action-Control-Plane-Bootstrap-Token: action-control-plane-bootstrap-admin-token" \
  -d '{"email":"platform-admin@example.com","display_name":"Platform Admin"}'
```

The response includes an `access_token` that can be used in an `Authorization: Bearer ...` header.

## Running Tests

```bash
make lint
make test
make package-check
```

## Running Acceptance Checks

```bash
make verify
make judge
```

## Containerized Stack

For the repeatable single-tenant pilot-shaped container workflow, see [CONTAINERIZED_DEPLOYMENT.md](CONTAINERIZED_DEPLOYMENT.md).

The short version is:

```bash
cp .env.compose.example .env.compose
make container-build
make container-up
```

## Working With Migrations

Apply migrations:

```bash
make migrate-up
```

Create a new revision after domain tables exist:

```bash
make migrate-revision MESSAGE="describe change"
```

## Configuration Notes

- Local development defaults to SQLite at `./var/action_control_plane.db`.
- Production mode rejects SQLite and requires docs to be disabled.
- Environment variables use the `ACTION_CONTROL_PLANE_` prefix.
- Local auth defaults to `development_signed_bearer`.
- Local signing defaults to development-local HMAC signing.
- Capability release defaults to `development_simulated`.
- Metrics and tracing are placeholder-only today; structured logs are the implemented observability path.

## Current Scope

This local setup boots the implemented finance-focused control-plane service. It is suitable for internal development and design-partner preparation work, but not for true production deployment. The biggest remaining gaps are enterprise identity, managed signing, real provider integrations, stronger isolation controls, and production operations hardening.
