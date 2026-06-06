# Production Trust Boundary Plan

## Purpose

This document describes how Actenon Cloud must move from a development-grade trust boundary to a production-grade one without confusing the control plane with the separate open kernel.

## What Exists Today

- Tenant-scoped APIs, persisted roles, memberships, service principals, and audit records exist.
- Action Intent intake, approvals, evidence, proof issuance, escrow, receipts, and audit traces are implemented.
- The service enforces some tenant visibility and mutation controls.
- Kernel-owned public contracts are pinned locally and validated at intake and receipt-ingestion time.

## What Is Simulated Today

- operator auth is development bearer-token based
- service auth is still a development-signed bearer flow
- proof signing is development-local HMAC
- capability release is development-simulated
- observability beyond structured logs is planned rather than implemented

## Control-Plane Versus Kernel Boundary

- The open kernel remains the source of execution semantics, verifier logic, and canonical execution-side artifacts.
- Actenon Cloud owns intake, governance, approval, evidence, issuance, escrow, receipt indexing, and audit.
- Production hardening must preserve this split. This repo should become a stronger issuer and system of record, not a replacement kernel.

## What Must Change For Production

- Replace development operator auth with enterprise identity and strong session binding.
- Replace service bearer assumptions with workload identity or token exchange rooted in trusted infrastructure.
- Move signing to managed key infrastructure with non-exportable keys.
- Replace simulated capability release with a real protected-resource integration.
- Enforce stronger tenant isolation at the data and runtime layers.
- Add production observability, deployment, rollback, backup, and incident-response controls.
- Automate compatibility checks against published kernel artifacts instead of only relying on locally pinned copies.

## Design-Partner Pilot Requirements

- explicit documentation of every simulated trust surface
- non-default secrets and isolated pilot environment
- managed database, object storage, TLS ingress, and log shipping
- named operators and limited tenant set
- manual operational oversight for proof issuance, escrow release, and receipt reconciliation

## Real Production Requirements

- enterprise operator identity
- workload identity for machine callers
- managed signing
- real capability release path
- stronger tenant isolation guarantees
- audited release and operations processes
