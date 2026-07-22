# Key Management Model

## Purpose

This document defines how Actenon Cloud should model signing keys and signing operations without storing raw key material in the control plane.

## Design Posture

- raw private key material stays in managed key infrastructure such as KMS or HSM systems
- the control plane stores only metadata, provider references, usage constraints, and signing lineage
- signing is used for control-plane artifacts such as PCCBs, attestations, or exports, not to replace kernel verifier semantics

## Core Entities

### SigningKeyReference

Represents a managed key that the control plane may ask an external provider to use. It includes:

- tenant scope or platform scope
- provider key reference
- algorithm
- intended key purpose
- current lifecycle state
- rotation policy reference
- custody or attestation reference

### SigningOperation Record

This record is now implemented in the repo as an early Release 1 control-plane audit primitive. It contains:

- requested artifact reference
- requested key reference
- digest or signing input reference
- request status
- provider operation correlation id
- completed signature reference
- operator or system actor

The current implementation records development-local signing operations and preserves room for future managed-provider correlation ids.

## Key Scope Model

Keys may exist at:

- tenant scope for tenant-specific proofs or export signatures
- platform scope for narrow shared functions with explicit audit controls

Release 1 should default to tenant-scoped keys where practical.

## Key Purposes

Allowed key purposes should be explicit and finite. Initial examples:

- PCCB signing
- approval attestation signing
- export signing
- receipt counter-signing

Do not use one generic "sign anything" key purpose.

## Lifecycle States

Recommended `SigningKeyReference.status` values:

- `ACTIVE`
- `ROTATING`
- `SUSPENDED`
- `REVOKED`
- `RETIRED`

Status applies to the control-plane ability to request sign operations. It does not imply deletion of provider-side material.

## Rotation Model

- Rotation policy should be explicit and stored as metadata or policy reference.
- New proofs should use the active key reference selected at issuance time.
- Previously issued artifacts remain linked to the historical key reference used for signing.
- Rotation should never rewrite old proof metadata.

## Access Control

- Only authorized platform or tenant administrators should manage key references.
- Normal approvers should not automatically gain key-management permissions.
- Break-glass or emergency key suspension actions should be audited heavily.

## Revocation And Quarantine Interaction

If a key reference is suspended or revoked:

- new proof issuance using that key should stop
- previously issued artifacts may require quarantine or reissuance review
- related artifact control state should capture the governance response

## Deferred Details

The receipt counter-signing service now defines a provider-neutral
non-exportable Ed25519 custody interface, two-approver lifecycle workflow,
historical `kid` publication, revocation timestamps, and durable operation
records. See [COUNTERSIGNING_SERVICE.md](COUNTERSIGNING_SERVICE.md).

Proof issuance signing remains separate. This pass intentionally does not lock
in:

- specific KMS or HSM vendors
- certificate chains
- hardware attestation format requirements
