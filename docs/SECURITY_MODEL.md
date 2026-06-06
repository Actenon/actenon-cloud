# Security Model

## Purpose

This document defines the security posture for Actenon Cloud at the architecture and domain-model level.

## Core Principles

- least privilege
- segregation of duties
- immutable auditability
- tenant isolation
- managed secrets and keys
- explicit trust boundaries around kernel and provider dependencies

## Principal Types

The control plane should recognize at least the following principal classes:

- human users
- tenant service principals
- platform service components
- platform administrators

Approver status is a capability granted through tenant membership and policy, not a separate identity type.

## Authorization Model

Authorization should combine:

- tenant membership
- role permissions
- finance approval entitlements
- workflow and policy context
- artifact control posture

Examples:

- a user may view an Action Intent but still lack permission to approve it
- an approver may approve a transfer up to a threshold but not a settlement instruction above that threshold
- a quarantined proof may be viewable but not exportable

## Separation Of Duties

Release 1 should support maker-checker controls for finance actions:

- the requester should not automatically satisfy required approval steps
- high-risk finance actions should require distinct approving principals
- policy changes should be auditable and may require separate administrative control

## Data Protection Model

- Canonical kernel Action Intent payloads and receipts should be stored immutably with digest references.
- Evidence objects should include integrity metadata and retention posture.
- Sensitive payloads should be encrypted at rest by infrastructure mechanisms.
- Secrets and key material must not be embedded in source control or application records.

## Auditability

The control plane should emit immutable audit events for:

- intake acceptance or rejection
- policy activation changes
- approval decisions
- proof issuance requests and outcomes
- receipt ingestion
- replay or reconciliation failures
- revocation and quarantine changes
- administrative or key-reference changes

## Trust Boundaries

### Open Execution Kernel

The kernel is trusted as the source of canonical execution and verifier artifacts, but compatibility must still be pinned and validated.

### External Providers And Adapters

Provider callbacks and hook responses are observations, not authoritative truth. They should be recorded with provenance and reconciled against receipts where possible.

### Managed Key Infrastructure

Key providers are trusted to hold raw key material. The control plane should only hold references, metadata, and signing lineage.

## Finance-Focused Controls

Release 1 should prioritize:

- approval thresholds and dual control
- replay protection through idempotency keys and consumption tracking
- evidence linkage for exceptions and manual overrides
- exportability for audits and reconciliation reviews

## Deferred Security Topics

The following remain intentionally deferred until implementation planning:

- exact identity provider protocol choices
- field-level encryption strategy
- regional data residency enforcement mechanics
- hardware-backed signing requirements for all proof types
- anomaly detection and behavior analytics
