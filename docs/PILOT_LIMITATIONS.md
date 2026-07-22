# Pilot Limitations

## Purpose

This document states the boundaries of the current invoice payment execution pilot and the limitations that must be stated plainly to design partners and internal teams.

## What The Pilot Is

The current pilot is a managed, single-tenant control-layer deployment for one governed invoice payment workflow. It is intended for supervised design-partner use with explicit operator support.

It is not a broad hosted product rollout.

## Current Truth By Area

### Deployment

- the current hosted posture is operator-run and single-tenant
- the repeatable deployment path is one application image plus one migration command
- deployment automation, rollback automation, and self-serve provisioning are not implemented

### Auth

- operator auth is still development-signed bearer auth with a bootstrap admin flow
- enterprise SSO, federation, and production workload identity are not implemented

### Signing

- proof issuance works with a development-local HS256 HMAC signer
- managed signing backends are modeled in code but not implemented

### Evidence Storage

- evidence metadata is persisted
- uploaded evidence is stored on a filesystem-backed writable path
- a native object-store upload path does not exist yet

### Observability

- structured logs and health endpoints exist
- request correlation exists
- metrics, tracing, alerting, and mature runbook automation do not

### Capability Release

- capability release remains simulated in this repo
- the pilot does not claim real protected-resource broker enforcement

## What The Pilot Does Not Do Yet

- it does not claim that Actenon Cloud itself executes invoice payments
- it does not claim that Actenon Cloud itself performs proof verification
- it does not claim production-ready identity, signing, storage, or observability
- it does not claim broad hosted multi-tenancy or self-serve SaaS onboarding
- it does not claim production-grade deployment automation, HA, or disaster recovery
- it does not claim finished payment-adapter integrations

## What Is Out Of Scope For This Pilot

- refunds
- batch payments
- multi-step treasury workflows
- generalized enterprise UI
- broad analytics and BI reporting
- a broad adapter marketplace

## Honest Pilot Claim

The honest claim for this pilot is narrower:

Actenon Cloud can already serve as a managed governance and traceability layer for one invoice payment execution workflow, but it still requires explicit operator support and substantial production-hardening work before broader hosted deployment should be considered.
