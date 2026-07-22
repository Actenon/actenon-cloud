# Live Pilot Overview

## Purpose

This document explains the current Actenon Cloud live pilot as one coherent managed system.

The scope is intentionally narrow:

- one managed single-tenant deployment
- one customer tenant in active use
- one governed outbound invoice payment workflow

It is not a broad hosted platform and not a generic finance operations suite.

## What Actenon Cloud Is In The Pilot

In the current pilot, Actenon Cloud is the managed control and traceability layer around one invoice payment workflow.

It is responsible for:

- intake of kernel-aligned Action Intents
- tenant policy evaluation
- approval and evidence routing
- proof issuance orchestration
- release-state tracking
- receipt linkage and audit trace access

It is not the kernel, not the verifier, and not the downstream payment execution system.

## What The Customer Sees

The customer sees a focused invoice payment workflow surface:

- an invoice payment action list
- a held and review queue
- an action detail view with lifecycle, approvals, evidence, proof, receipt, and audit trace visibility
- narrow approval and evidence actions where the backend supports them
- trace export and audit views
- a small usage summary for the current reporting period

The product surface is meant to answer:

- what happened to this invoice payment
- why it was allowed, held, or refused
- what still needs review
- what artifacts, proof records, and receipts are linked to it
- how much governed workflow activity has happened in the reporting period

## How The Pilot Is Deployed

The honest hosted pilot shape today is:

- one application runtime
- one migration step from the same image
- one managed PostgreSQL database
- one mounted persistent filesystem-backed evidence path
- one TLS ingress or reverse proxy
- one central log collection path

Optional backup or export infrastructure may exist around the pilot, but live uploaded evidence in the current repo is still filesystem-backed.

## End-To-End Pilot Flow

1. A customer or upstream system submits an invoice payment Action Intent.
2. Actenon Cloud validates the payload against the pinned kernel-facing contract.
3. Tenant policy classifies the action as `allow`, `deny`, `approval_required`, `needs_evidence`, or `structurally_non_executable`.
4. If required, customer operators complete approval or evidence steps.
5. Actenon Cloud may issue a bounded proof for the exact action.
6. Actenon Cloud may move the action through release-state tracking.
7. Downstream payment execution happens outside this repo.
8. A kernel-aligned receipt is ingested and linked back into the action trace.

## What The Customer Owns

The customer owns the workflow operation inside the pilot:

- reviewing held actions
- approving or declining when assigned and authorized
- supplying or registering evidence when required
- interpreting intended policy blocks and business exceptions
- reviewing receipts, reconciliations, and exported traces
- participating in the weekly operating cadence

## What The Provider Owns

The provider owns the managed pilot service:

- deployment and release execution
- database, storage, TLS, logging, and secret handling
- access bootstrap in the current early auth model
- hosted-environment incident triage
- support for policy, mapping, and access changes during the pilot
- documentation of current limitations and next-step hardening work

## How Usage And Value Are Measured

The pilot now includes tenant-scoped reporting for:

- submitted actions
- proved and allowed actions
- blocked or refused actions
- reviewed actions
- receipt-linked actions

These numbers are meant to support:

- weekly pilot reporting
- operator trust and adoption discussion
- ROI discussion with the design partner
- future per-action pricing design

This is metering only. It is not a billing system.

Blocked or refused actions remain visible because they demonstrate prevention value, but they are not treated as usage-billed actions.

## What Is Still Manual Or Early

The live pilot remains honest about current limits:

- auth is still early and provider-assisted
- signing is still development-local unless upgraded separately
- capability release is still simulated
- uploaded evidence is still stored on mounted filesystem storage
- some exception classes still end in manual follow-up outside the product
- observability is still operator-oriented and pilot-grade, not a full SRE stack
- proof verification remains outside this repository through a separate verifier boundary

## What A Successful Pilot Proves

A successful pilot proves that one customer can use Actenon Cloud as a managed control layer for:

- invoice payment decision visibility
- approvals and evidence progression
- bounded proof packaging
- receipt linkage
- audit-trace review
- period usage reporting

It does not prove:

- broad self-serve delivery
- finished production hosting
- in-repo proof verification
- direct payment execution by this repo
- finished enterprise auth, signing, storage, or observability maturity

## Best Related Docs

- [CUSTOMER_HANDOFF_GUIDE.md](CUSTOMER_HANDOFF_GUIDE.md)
- [DEPLOYMENT_AND_OPERATIONS_INDEX.md](DEPLOYMENT_AND_OPERATIONS_INDEX.md)
- [HOSTING_AND_DEPLOYMENT_STATUS.md](HOSTING_AND_DEPLOYMENT_STATUS.md)
- [PILOT_LIMITATIONS.md](PILOT_LIMITATIONS.md)
- [USAGE_METERING.md](USAGE_METERING.md)
- [docs/OPEN_KERNEL_DEPENDENCY_MODEL.md](docs/OPEN_KERNEL_DEPENDENCY_MODEL.md)
