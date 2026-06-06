# Audit API

## Purpose

This document defines the first audit and trace query APIs in Actenon Cloud.

These APIs are meant to make finance action traces understandable and exportable for operators and auditors. They are not a replacement for enterprise reporting or analytics systems.

## Endpoints

### `GET /api/v1/audit/events`

Lists durable audit events.

Current filters:

- `tenant_id`
- `action_intent_record_id`
- `receipt_id`
- `subject_type`
- `subject_id`
- `event_type`

### `GET /api/v1/audit/events/{audit_event_id}`

Returns one audit event.

### `GET /api/v1/audit/reconciliation`

Lists reconciliation records.

Current filters:

- `tenant_id`
- `action_intent_record_id`
- `receipt_id`
- `reconciliation_type`
- `status`

### `GET /api/v1/audit/reconciliation/{reconciliation_record_id}`

Returns one reconciliation record.

### `GET /api/v1/audit/traces/{action_intent_record_id}`

Returns the current finance action trace bundle for one Action Intent.

The trace currently includes:

- Action Intent summary
- approval requests
- approval decisions
- evidence objects
- issued proofs
- escrow records
- receipts
- reconciliation records
- audit events

### `GET /api/v1/audit/export?action_intent_record_id=...`

Returns an export-oriented bundle for one Action Intent trace.

Release 1 export is JSON-only and synchronous.

## Audit Event Model

The current `AuditEvent` record stores:

- tenant linkage
- Action Intent linkage when available
- receipt, proof, and escrow linkage when available
- event category
- event type
- subject type and subject id
- actor principal
- structured event payload
- creation timestamp

Current event categories implemented in this pass:

- `receipt`
- `reconciliation`

## Trace Use

The trace API is the main Release 1 query surface for understanding a finance action path end to end.

It is designed to answer questions such as:

- which approvals existed for this action
- which evidence supported approval
- which proof was issued
- which escrow capability was released
- which receipt was ingested
- whether reconciliation matched or needs review

## Release 1 Limits

This API intentionally does not yet provide:

- long-running export jobs
- tenant-admin authorization surfaces
- BI-style aggregations
- advanced paging and saved searches
- cross-tenant audit views
