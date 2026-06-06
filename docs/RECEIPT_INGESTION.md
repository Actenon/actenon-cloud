# Receipt Ingestion

## Purpose

This document defines the first receipt-ingestion implementation in Actenon Cloud.

The goal is to make the control plane the central searchable receipt fabric above the open execution kernel without redefining kernel receipt semantics.

## Boundary

The control plane now:

- validates an incoming kernel receipt against a pinned versioned contract reference
- stores the canonical receipt payload immutably in the control-plane record
- indexes receipt fields for finance search
- links receipts to Action Intents, proofs, escrow records, approvals, decisions, and evidence
- emits reconciliation records and audit events around ingestion

The control plane still does not:

- redefine kernel receipt semantics
- treat provider callbacks as authoritative truth instead of receipts
- build broad analytics or reporting layers

## Current External Contract

Because the open kernel repo is not present in this workspace, the current implementation uses a pinned local development copy of the external contract:

- `schemas/kernel/receipt.finance.v1alpha1.schema.json`

Current version reference:

- `open_execution_kernel.receipt.finance.v1alpha1`

This is a local development assumption, not a claim that the kernel publication path is finalized.

## Endpoint

### `POST /api/v1/receipts`

Ingests a kernel-aligned finance receipt, validates it, links it to the governed finance trace, and persists reconciliation metadata.

### `GET /api/v1/receipts`

Searches receipt records across the current indexed fields.

### `GET /api/v1/receipts/{receipt_id}`

Returns a single persisted receipt record.

## Request Shape

The current ingest request includes:

- `tenant_id`
- `action_intent_record_id`
- `issued_proof_id` optional
- `escrow_record_id` optional
- `kernel_contract_ref`
- `kernel_receipt`
- `received_by`

The embedded `kernel_receipt` is validated against the pinned external contract.

## Current Receipt Fields

The pinned finance receipt contract currently expects:

- `receipt_id`
- `intent_id`
- `receipt_type`
- `outcome`
- `occurred_at`
- `action_intent_digest`
- `action_type`
- `amount_minor`
- `currency`

Optional comparison fields currently supported:

- `source_account_ref`
- `destination_account_ref`
- `provider_execution_ref`
- `settlement_reference`
- `proof_nonce`
- `audience`
- `scope`

## Persistence Behavior

On successful ingest, the service persists:

- the canonical receipt payload
- the receipt digest
- receipt indexing fields for finance search
- linked approval request, approval decision, and evidence identifiers
- direct linkage to issued proof and escrow record when provided
- reconciliation summary

The receipt record is idempotent by tenant plus payload digest.

## Search Behavior

The current `GET /api/v1/receipts` filters support:

- `tenant_id`
- `action_intent_record_id`
- `issued_proof_id`
- `escrow_record_id`
- `receipt_type`
- `outcome`
- `currency`
- `provider_execution_ref`

This keeps Release 1 queryable for finance operators without overbuilding analytics.

## Action Intent Lifecycle Effects

Receipt ingestion updates the linked `ActionIntentRecord` by:

- setting `latest_receipt_id`
- moving `receipt_state` to `indexed` or `reconciled`
- moving `execution_state` to `result_observed`, `failure_observed`, or `dispatch_confirmed` based on receipt outcome

## Release 1 Limits

This pass intentionally does not implement:

- receipt supersession workflows
- replay or stream cursor management
- broad aggregation analytics
- automatic proof invalidation based on receipt semantics
- cross-tenant export jobs
