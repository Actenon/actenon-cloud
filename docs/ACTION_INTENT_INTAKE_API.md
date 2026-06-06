# Action Intent Intake API

## Purpose

This document defines the first Action Intent intake API for Actenon Cloud.

## Boundary

The API accepts a control-plane intake envelope that contains a canonical external Action Intent object. The control plane validates that object against a versioned external contract reference and stores the intake record plus policy decision outcome.

The open kernel repository is not present in this workspace. Because of that, the current implementation uses a pinned local development copy of a versioned external contract at:

- `schemas/kernel/action_intent.finance.v1alpha1.schema.json`

This is an implementation assumption for local development, not a claim that the kernel publication model is final.

## Endpoints

### `POST /api/v1/action-intents`

Accepts a control-plane intake envelope and returns a persisted intake record plus decision outcome.

### `GET /api/v1/action-intents`

Lists persisted Action Intent records for pilot operator review.

Current filters:

- `tenant_id`
- `workflow_key`
- `decision_state`
- `approval_state`
- `evidence_state`
- `execution_state`
- `receipt_state`
- `external_reference`

### `GET /api/v1/action-intents/{action_intent_record_id}`

Returns a persisted intake record by control-plane record identifier.

## Request Shape

The request uses the control-plane envelope, but the embedded `kernel_action_intent` object is validated against the external versioned contract referenced by `kernel_contract_ref`.

Key fields:

- `tenant_id`
- `submission_id`
- `idempotency_key`
- `requested_by`
- `kernel_contract_ref`
- `kernel_action_intent`
- `workflow_binding` optional
- `finance_routing_context` optional
- `evaluation_context` optional dynamic inputs for deterministic policy evaluation

## Current Supported External Contract

Current version reference:

- `open_execution_kernel.action_intent.finance.v1alpha1`

Current finance-focused fields in that pinned contract include:

- `intent_id`
- `workflow_key`
- `action_type`
- `amount_minor`
- `currency`
- `source_account_ref`
- `destination_account_ref`
- `destination_country` optional
- `evidence_refs` optional
- `requested_execution_date` optional

## Intake Behavior

The service currently performs:

1. tenant existence and status checks
2. idempotency lookup by `tenant_id` plus `idempotency_key`
3. external contract validation for `kernel_action_intent`
4. finance index extraction for search and policy evaluation
5. active tenant workflow policy lookup
6. deterministic decision evaluation
7. persistence of the intake record, payload digest, validation status, decision state, workflow requirement snapshots, and evaluation trace
8. automatic creation of approval requests when policy requires approval
9. initialization of evidence workflow state when policy requires evidence

## Decision States

The current intake path produces one of:

- `allow`
- `deny`
- `approval_required`
- `needs_evidence`
- `structurally_non_executable`

`structurally_non_executable` is reserved for hard-rule and contract-shape failures, not tenant policy rules.

## Response Fields

The intake response includes:

- control-plane record identifier
- selected policy reference if available
- external contract family and version
- contract validation status and errors
- decision state and reason
- matched rule identifier if any
- aggregate `approval_state`
- aggregate `evidence_state`
- coarse `execution_state`
- snapped `approval_requirement` if present
- snapped `evidence_requirement` if present
- finance index
- stored Action Intent payload
- evaluation trace
- `idempotent_replay`

The list response is intentionally narrower and optimized for the invoice payment operator queue. It includes:

- Action Intent identifiers
- tenant and workflow scope
- external reference
- requester identity
- amount and currency when present in the finance index
- source and destination account references when present
- decision, approval, evidence, execution, and receipt states
- latest receipt linkage
- timestamps

## Idempotency

If the same tenant replays the same `idempotency_key`, the API returns the existing persisted record instead of creating a second record.

## Hard Rules

Before policy rules run, the service applies hard rules for:

- unsupported external contract version
- contract validation failure
- conflicting intake hints versus canonical Action Intent fields
- identical source and destination accounts

These rules are deterministic and always run before tenant policy evaluation.
