# Signing And Keys

## Purpose

This document defines the first signing-key abstraction and signing-operation model for Actenon Cloud.

## Boundary

The control plane now models signing keys and signing operations explicitly, but it still does not claim production-grade managed-key maturity.

Current scope:

- key references
- basic lifecycle state
- issuer metadata
- local development signing
- durable signing-operation audit records

Deferred proof-issuance scope:

- provider-specific KMS or HSM adapters
- certificate chains
- production asymmetric signing workflows

## Current Endpoints

- `POST /api/v1/issuance/keys`
- `GET /api/v1/issuance/keys`
- `GET /api/v1/issuance/keys/{signing_key_reference_id}`
- `POST /api/v1/issuance/keys/{signing_key_reference_id}/activate`
- `POST /api/v1/issuance/keys/{signing_key_reference_id}/suspend`

## Current Key Model

Each `SigningKeyReference` stores:

- tenant scope
- display name
- issuer name and issuer URI
- trust tier
- explicit key purpose
- declared algorithm
- backend type
- provider key reference
- optional public key reference
- lifecycle metadata
- lifecycle timestamps

## Key Purposes

The current finite purpose set is:

- `pccb_signing`
- `approval_attestation_signing`
- `export_signing`

Release 1 proof issuance uses `pccb_signing`.

## Lifecycle States

The current key lifecycle state set is:

- `active`
- `suspended`
- `revoked`
- `retired`

The implemented lifecycle actions are intentionally minimal:

- activate
- suspend

Revocation and retirement are modeled for future governance flows but are not yet exposed as public APIs.

## Local And Development Signing

The implemented signer is intentionally narrow:

- backend: `development_local_hmac`
- algorithm: `HS256`
- secret source: runtime configuration only

This signer is for local and test environments. It exists so the proof issuance path is real and testable today.

It is not a claim that local HMAC signing is acceptable for production finance proof issuance.

## External Managed Keys

The model also supports:

- backend: `external_managed`
- asymmetric algorithm metadata such as `RS256` or `ES256`

This is a modeling surface only right now. Managed external signing requests are not implemented in this repo pass. If selected, issuance will reject rather than pretending a provider call succeeded.

## Signing Operation Records

Each successful or failed signing attempt persists a `SigningOperationRecord` with:

- requested proof reference
- key reference
- algorithm
- backend
- payload digest
- signature if produced
- provider operation reference placeholder
- failure detail if signing failed
- request and completion timestamps

This makes the issuance path auditable even in the current development implementation.

## Issuer Identity And Trust Metadata

Issuer identity is carried on the key reference and copied onto the proof at issuance time:

- `issuer_name`
- `issuer_uri`
- `trust_tier`

This prevents later key changes from rewriting the historical issuer metadata attached to an already issued proof.

## What Is Deferred

- KMS or HSM provider adapters
- per-tenant secret isolation for development signing
- rotation policies and automatic rollover
- proof revocation signing
- hardware attestation evidence
- multi-party or threshold signing

## Receipt Counter-Signing

Receipt counter-signing is intentionally separate from proof issuance. The
implemented service:

- emits the public `receipt_countersignature v1` format
- calls a non-exportable Ed25519 HSM/KMS interface
- publishes active and historical public keys by `kid`
- requires requester separation and two independent lifecycle approvers
- records signing and lifecycle access
- supports rotation and revocation without deleting historical public keys

See [COUNTERSIGNING_SERVICE.md](COUNTERSIGNING_SERVICE.md) and the
[compromise recovery runbook](operations/COUNTERSIGNING_KEY_COMPROMISE_RECOVERY.md).
