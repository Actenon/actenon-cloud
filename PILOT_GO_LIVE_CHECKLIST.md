# Pilot Go Live Checklist

## Purpose

This checklist defines the minimum pre-go-live bar for a managed single-tenant invoice payment pilot.

## Environment

- [ ] One dedicated pilot hostname is assigned.
- [ ] TLS is configured and verified for the pilot hostname.
- [ ] The reverse proxy or ingress is configured to forward traffic to the app runtime.
- [ ] The hosted pilot uses one dedicated runtime deployment boundary.

## Database And Migrations

- [ ] Managed PostgreSQL is provisioned for the pilot.
- [ ] The application database URL points at the intended pilot database.
- [ ] A pre-go-live database backup or snapshot exists.
- [ ] `alembic upgrade head` succeeds against the target database.

## Evidence And Storage

- [ ] The mounted evidence storage path exists and is writable by the application runtime.
- [ ] A dedicated object storage bucket or namespace exists for backup or export use.
- [ ] Operators understand that uploaded evidence is still written to the mounted filesystem path today.

## Secrets And Runtime Configuration

- [ ] Default bootstrap and signing secrets are not used.
- [ ] Interactive docs are disabled unless the pilot is a protected sandbox.
- [ ] Issuer metadata uses pilot-specific values.
- [ ] The hosted environment template has been reviewed and tailored for the pilot.

## Logging And Operations

- [ ] App logs are collected centrally.
- [ ] Reverse proxy logs are collected centrally.
- [ ] Named engineering and operator owners are assigned.
- [ ] Backup responsibility is assigned for database and evidence storage.

## Verification

- [ ] `GET /api/v1/health/live` succeeds through the deployed endpoint.
- [ ] `GET /api/v1/health/ready` succeeds through the deployed endpoint.
- [ ] The invoice payment action list loads.
- [ ] The held and exceptions queue loads.
- [ ] One action detail page renders correctly.

## Pilot Truth Acknowledgement

- [ ] The pilot team understands that auth is still early.
- [ ] The pilot team understands that signing is still early unless separately upgraded.
- [ ] The pilot team understands that capability release is still simulated.
- [ ] The pilot team understands that proof verification remains external through a separate verifier repo or verifier interface.
