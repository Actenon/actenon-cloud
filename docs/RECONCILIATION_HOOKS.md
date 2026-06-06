# Reconciliation Hooks

## Purpose

This document defines how reconciliation and lifecycle hooks are represented in the current Actenon Cloud implementation.

## Representation

Release 1 represents reconciliation hooks as durable `ReconciliationRecord` rows emitted during receipt ingestion.

Each hook records:

- the Action Intent being reconciled
- the receipt that triggered reconciliation
- the proof and escrow references when present
- the reconciliation type
- the reconciliation status
- a human-readable summary
- structured field-by-field checks
- the hook name

The current hook name is:

- `receipt_ingestion`

## Current Hook Types

The implemented reconciliation types are:

- `intent_to_receipt`
- `proof_to_receipt`
- `escrow_to_receipt`

## Current Statuses

The implemented reconciliation statuses are:

- `matched`
- `manual_review_required`
- `mismatch`

## Trigger Point

Hooks currently run immediately after a receipt is stored and indexed.

The sequence is:

1. validate the kernel receipt contract
2. persist the receipt record
3. emit `receipt.ingested`
4. run reconciliation checks
5. persist reconciliation records
6. emit reconciliation audit events
7. update Action Intent lifecycle state from the receipt outcome

## Current Comparisons

### Intent To Receipt

Compares:

- intent id
- action intent digest
- action type
- amount
- currency

### Proof To Receipt

When a proof is linked, compares:

- proof nonce when provided by the receipt
- audience when provided by the receipt
- scope when provided by the receipt
- action intent digest

### Escrow To Receipt

When an escrow record is linked, compares:

- provider execution reference when available
- action intent digest
- scope when provided by the receipt

## Lifecycle Effects

These hooks also update coarse Action Intent lifecycle state:

- receipt outcome `succeeded` -> `execution_state=result_observed`
- receipt outcome `failed` -> `execution_state=failure_observed`
- receipt outcome `pending` -> `execution_state=dispatch_confirmed`

Receipt lifecycle state becomes:

- `reconciled` when all active reconciliation hooks match
- `indexed` when manual review or mismatch remains

## Why This Is Narrow

This is intentionally a small, auditable hook model rather than a full rules engine.

It does not yet implement:

- configurable reconciliation policies
- replay consumers
- asynchronous lifecycle orchestration
- automatic revocation or quarantine based on reconciliation failures
- enterprise workflow escalation
