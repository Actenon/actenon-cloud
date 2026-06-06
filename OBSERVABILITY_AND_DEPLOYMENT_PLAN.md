# Observability And Deployment Plan

## Purpose

This document defines the minimum path from the current developer-friendly runtime to a pilot-credible and production-hardened operations posture.

## What Exists Today

- structured application logs with request correlation
- liveness and readiness endpoints
- persisted audit events, reconciliation records, and trace-export surfaces
- migration and test automation through CI and `verify.sh`
- an explicit observability placeholder in the runtime startup path

## What Is Simulated Today

- metrics exporters are not implemented
- tracing exporters are not implemented
- alerting is not implemented
- deployment automation is not implemented
- backup, restore, and disaster recovery are not implemented

## Design-Partner Pilot Requirements

- central log shipping
- basic service and database dashboards
- managed PostgreSQL and persistent evidence storage
- TLS ingress
- one documented deployment topology
- one operator runbook for health checks, migrations, rollback, and incident triage
- one explicit internal observability document and one hosted-pilot verification checklist

## What Must Change For Production

- add metrics
- add tracing
- add alerting
- implement deployment automation and environment promotion controls
- replace or harden the current filesystem evidence storage path with a production-grade storage integration
- define backup, restore, and disaster recovery procedures
- exercise rollback and migration recovery paths

## Real Production Target

- metrics, tracing, and alerting wired to managed backends
- repeatable deployment pipeline
- tested backup and restore
- runbooks attached to real on-call operations
