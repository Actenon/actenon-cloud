# Proof Issuance

## Purpose

This document defines the first bounded proof issuance path in Actenon Cloud.

Release 1 issues control-plane proofs for finance actions that have passed the required governance checks. It does not embed kernel verifier logic and it does not redefine kernel proof semantics.

## Boundary

The control plane issues proofs about control-plane facts:

- the exact Action Intent digest
- the tenant policy outcome
- approval satisfaction
- evidence satisfaction
- the requested audience and scope

The control plane does not claim to verify kernel execution, kernel receipts, or kernel-native proofs.

## Current Endpoints

- `POST /api/v1/issuance/proofs`
- `GET /api/v1/issuance/proofs`
- `GET /api/v1/issuance/proofs/{issued_proof_id}`

## Current Issuance Rules

Proof issuance is deterministic. The service currently checks:

- Action Intent contract validation must be `valid`
- policy result must not be `deny` or `structurally_non_executable`
- if approvals are required, `approval_state` must be `satisfied`
- if evidence is required, `evidence_state` must be `satisfied`
- a scope-bound audience must be provided
- an active signing key for `pccb_signing` must be available

If these checks fail, the service persists a rejected issuance record with the failed checks and reason.

## Current Proof Shape

The proof payload is a signed JSON document that includes:

- `proof_kind`
- issuer identity and trust tier
- subject tenant and Action Intent identifiers
- exact `action_intent_digest`
- exact `audience`
- exact `scope`
- `scope_hash`
- `nonce`
- `issued_at`
- `expires_at`
- policy and workflow governance state
- finance binding fields such as action type, amount, and currency

This makes the proof bounded to:

- one Action Intent hash
- one audience
- one scope set
- one issuance window

## Persistence

Each issuance attempt now persists an `IssuedProof` record containing:

- proof status
- issuer metadata
- Action Intent digest binding
- audience and scope binding
- nonce
- payload digest
- signature if issuance succeeded
- failure reason if issuance was rejected or failed
- revocation-ready metadata fields
- issuance trace for auditability

Successful signing also persists a `SigningOperationRecord`.

## Idempotency

If a still-valid proof already exists for the same:

- tenant
- Action Intent
- proof kind
- audience
- scope hash
- Action Intent digest

the service returns the existing proof instead of minting a second one.

## Finance-Focused Release 1 Example

The current implementation is aimed first at finance actions such as payments and transfers where the control plane needs to attest:

- which transfer intent was approved
- which audience may rely on the attestation
- which bounded finance scopes it covers
- that approvals and evidence were satisfied at issuance time

## What Is In Scope Now

- proof issuance for control-plane-governed finance actions
- deterministic eligibility checks
- exact audience, scope, nonce, and action-hash binding
- persisted issuance and signing records
- expiry handling for issued proofs
- revocation-ready metadata fields on proof records

## What Is Deferred

- receipt-bound issuance rules
- escrow-bound issuance rules
- verifier-side proof validation
- multi-artifact proof bundles
- proof revocation APIs and governance flows
- kernel receipt ingestion prerequisites for stronger proofs
