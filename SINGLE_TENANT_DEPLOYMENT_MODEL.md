# Single-Tenant Deployment Model

## Purpose

This document defines how Actenon Cloud should be hosted for the current invoice payment pilot: one operationally isolated managed deployment per design partner.

## Core Model

For the current pilot stage, one design partner should receive:

- one dedicated app runtime deployment
- one dedicated migration path for that deployment
- one dedicated PostgreSQL database boundary
- one dedicated mounted evidence storage path
- one dedicated ingress hostname
- one dedicated log scope
- one dedicated secret set

This is operational single-tenancy first, even though the application itself still supports platform and tenant abstractions internally.

## Day-To-Day Operating Shape

The expected real operating posture is:

- one real customer organization per deployment
- one customer organization per deployment
- one primary live pilot tenant inside that deployment
- one provider-managed operator team responsible for deployment and incident handling
- no self-serve tenant creation
- no expectation that unrelated customers share the same runtime
- the pilot should not be run like a general shared SaaS environment

## Why Single-Tenant First Is The Right Hosted Shape

For the current maturity level, single-tenant hosting is the most supportable model because it:

- keeps blast radius small
- keeps customer trust boundaries legible
- makes evidence storage and backup scope obvious
- simplifies incident triage
- avoids premature shared-SaaS assumptions while auth, signing, and hosting posture remain early

## Concrete Deployment Boundary

One pilot deployment boundary includes:

- the Actenon Cloud web runtime
- the migration invocation used for that runtime
- the PostgreSQL data boundary
- the persistent evidence filesystem boundary
- ingress and TLS boundary
- log collection boundary
- secret boundary
- backup boundary for DB and evidence

It excludes:

- the separate verifier repo or verifier runtime
- the separate kernel repo
- shared customer hosting
- self-serve onboarding flows

## Storage Reality Inside The Deployment

### Live Evidence Path

The current runtime stores uploaded evidence on a mounted filesystem path.

That means each hosted pilot should have:

- one dedicated writable evidence path
- clear backup coverage for that path
- no claim that live evidence already writes to object storage

### Object Storage

If object storage is provisioned for the pilot, it should be treated as:

- backup support
- export support
- future hardening support

It should not be described as the current primary storage layer for uploaded evidence.

## Automation Boundary

### Reasonable To Automate In Hosting

- container restart behavior
- managed database service operations
- ingress forwarding
- log shipping
- scheduled DB backups through the managed database provider

### Still Manual Or Explicitly Operator-Owned

- migration timing
- deployment approval
- operator bootstrap strategy
- TLS certificate setup if not platform-managed
- evidence backup verification
- restore execution
- rollback decisions

## What This Model Does Not Mean

This model does not imply:

- broad hosted multi-tenancy
- production SaaS maturity
- per-customer self-serve environments
- automatic horizontal scaling
- full disaster-recovery automation

## Revisit Later, Not Now

If the pilot succeeds, later work can revisit:

- native object-storage evidence writes
- stronger hosted identity bootstrap
- shared infrastructure across customers
- production-grade release automation

Those are follow-on decisions, not assumptions for the current hosted pilot model.
