# Pilot Environment Requirements

## Purpose

This document defines the minimum environment bar for a design-partner pilot.

## Minimum Environment

- isolated pilot environment
- TLS ingress
- managed PostgreSQL
- mounted persistent evidence storage
- central log shipping
- non-default secrets
- one named operator owner and one named engineering owner

## Configuration Expectations

- `ACTION_CONTROL_PLANE_ENVIRONMENT=staging` or another non-local pilot profile
- interactive docs disabled unless explicitly needed for a protected pilot sandbox
- SQLite prohibited
- default bootstrap and signing secrets prohibited
- pilot issuer metadata must use pilot-specific domains and labels

## Health And Readiness Expectations

- `live` proves the API process is serving
- `ready` proves the API process, database, and evidence storage path are usable
- pilot operations must treat readiness failures as blocking
- a pilot must not rely on the presence of metrics or tracing exporters that are not yet implemented

## Pilot-Specific Cautions

- auth is still early and not equivalent to enterprise SSO
- signing is still early unless moved to managed infrastructure
- capability release remains simulated until an external broker is integrated
- uploaded evidence is currently stored on a filesystem path, not through a managed object storage adapter
- manual operator oversight is still required for sensitive finance workflows

## Real Production Delta

The following are still required beyond pilot:

- enterprise SSO
- workload identity
- managed signing
- real external capability release
- production-grade evidence storage hardening beyond the current mounted filesystem path
- metrics, tracing, and alerting
- backup, restore, and disaster recovery

## Supporting Hosted Pilot Artifacts

- `deploy/env/hosted-pilot.env.example`
- `deploy/nginx/action-control-plane.conf`
- `TLS_SETUP.md`
- `DATABASE_AND_MIGRATIONS.md`
- `OBJECT_STORAGE_CONFIGURATION.md`
- `LOGGING_COLLECTION.md`
- `BACKUP_RESTORE_ASSUMPTIONS.md`
- `PILOT_GO_LIVE_CHECKLIST.md`
