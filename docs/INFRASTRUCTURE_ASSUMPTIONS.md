# Infrastructure Assumptions

## Purpose

This document states the minimum infrastructure assumptions behind the current hosted single-tenant Actenon Cloud pilot model.

It is concrete enough to operate, but intentionally narrower than a general cloud platform design.

## App Runtime Assumptions

- the app runs as one containerized web service
- the pilot UI is served from that same runtime
- migrations run as a separate command from the same image
- no worker process is required
- no queue broker is required

## Database Assumptions

- hosted pilot uses managed PostgreSQL
- the pilot has a dedicated database boundary
- the database is reachable from the app runtime and approved operator paths only
- managed database backups should be enabled at the provider layer
- schema rollback is not automatic

## Evidence Storage Assumptions

### Required Live Storage

- the runtime requires a mounted writable filesystem path for evidence uploads
- the path must persist across runtime restarts
- the path must be writable by the app runtime user
- the path must be included in backup scope

### Optional Adjacent Object Storage

- object storage may be provisioned for backup copies or export bundles
- object storage is not required for app boot
- object storage is not yet the primary live evidence write path

## TLS And Ingress Assumptions

- one pilot-specific hostname exists
- TLS terminates at ingress or reverse proxy, not inside the app process
- inbound access is limited to approved pilot operators and integration paths
- certificate lifecycle is manual unless the hosting platform already automates it

## Logging Assumptions

- application logs are shipped centrally
- logs remain structured JSON
- log access is scoped to the pilot operator team
- logs are the primary operational signal today because metrics and tracing remain limited

## Secret Handling Assumptions

- secrets are injected by the hosting environment
- secrets are not baked into container images
- non-default values are required for:
  - database credentials
  - bootstrap admin token
  - signing secret
- rotation is still an operator-managed action during the pilot

## Backup Assumptions

- managed database backup is enabled
- evidence filesystem backup or snapshot coverage is enabled
- restore steps remain operator-run, not product-automated
- backup verification is a pilot operating duty, not yet a finished platform feature

## Monitoring Assumptions

- `/api/v1/health/live` is used for basic process liveness
- `/api/v1/health/ready` is used as the blocking readiness signal
- readiness is not acceptable if either:
  - database is unavailable
  - evidence storage is unavailable
- central logs are reviewed during deployment and incident handling
- metrics, tracing, and alerting should not be overstated

## Identity And Bootstrap Assumptions

- the hosted pilot still needs an explicit operator bootstrap strategy outside the local compose profile
- the current repo-native bootstrap and dev token issuance flows are not the full hosted answer
- hosted operation should assume deliberate operator-controlled bring-up rather than self-serve admin creation

## Boundary Assumptions

- kernel contracts remain outside this repo
- proof verification remains outside this repo
- this model is for managed pilot hosting only
- this model does not imply self-serve SaaS readiness
