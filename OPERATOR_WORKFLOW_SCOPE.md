# Operator Workflow Scope

## Purpose

This document defines the minimum operator workflows that must be supported for the invoice payment execution pilot.

It is scoped to customer-operable workflow actions inside a managed single-tenant deployment.

## Operator Roles In Scope

The pilot only needs a small workflow role set:

- finance reviewer
- approver
- evidence contributor
- payment requester
- technical operator

These are workflow roles, not a claim that the product already has a full role-management UI.

## Minimum Workflow Coverage

### 1. Held And Exceptions Queue

The operator must be able to:

- identify held actions that are reviewable now
- distinguish blocked final outcomes from reviewable held actions
- identify exceptions that still require manual follow-up
- open one action into the detailed review surface

This depends on:

- a dedicated held and exceptions queue
- Action Intent list data
- proof state summaries

### 2. Payment Request Visibility

The requester or reviewer must be able to:

- find the invoice payment action
- read current lifecycle state
- understand whether it was allowed, held, denied, or structurally blocked

This depends on:

- an Action Intent queue
- Action Intent detail
- audit trace detail

### 3. Approval Review

The approver must be able to:

- identify actions waiting for approval
- inspect the payment summary
- inspect the decision explanation
- inspect linked evidence
- approve or reject when the current token is assigned to the open approval request

This depends on:

- `POST /api/v1/approvals/{approval_request_id}/decisions`
- evidence metadata and, ideally, evidence content access

### 4. Evidence Resolution

The operator must be able to:

- identify actions waiting for evidence
- upload evidence when the current token has tenant evidence write access
- register external evidence when the current token has tenant evidence write access
- confirm whether evidence is now satisfied or still missing

This depends on:

- `GET /api/v1/evidence`
- `POST /api/v1/evidence/upload`
- `POST /api/v1/evidence/register`
- `GET /api/v1/action-intents/{action_intent_record_id}`

### 5. Proof, Release, And Receipt Visibility

The reviewer or technical operator must be able to:

- inspect proof stage
- inspect release or escrow stage
- inspect execution state
- inspect receipt and reconciliation results
- understand whether the action completed, failed, or still needs manual follow-up

This depends on:

- `GET /api/v1/issuance/proofs`
- `GET /api/v1/audit/traces/{action_intent_record_id}`
- `GET /api/v1/audit/export?action_intent_record_id=...`

## Minimum Operator Actions Required

The UI only needs to support these operator actions directly:

- open held and exceptions queue
- open action detail
- approve when assigned and permitted
- reject when assigned and permitted
- upload evidence when permitted
- register external evidence when permitted
- export trace

## Actions That Do Not Need First-Class UI Yet

The pilot does not need first-class UI support for:

- tenant creation
- role creation
- service-principal management
- policy authoring
- signing-key lifecycle administration
- cross-tenant audit views
- proof issuance controls
- escrow release controls
- receipt ingestion controls
- escalation case management

Those can stay API-driven or internal-operator-only for this stage.

## Required State Visibility

Every action detail view should show the current values of:

- `decision_state`
- `approval_state`
- `evidence_state`
- `execution_state`
- `receipt_state`

Where present, the operator should also see:

- proof status
- escrow status
- reconciliation status

## Minimum Backend Gaps That Matter

### Evidence Review Gap

Approval review is weaker than it should be unless uploaded evidence can be opened safely from the UI.

Minimum addition if in-product evidence review is required:

- controlled evidence download or presigned access

### Escalation And Follow-Up Gap

The current workflow can classify items as manual follow-up, but it does not persist:

- operator notes
- escalation ownership
- follow-up due dates
- in-product escalation status

## Customer-Facing Versus Internal Operator Scope

Customer-facing workflow scope:

- payment queue
- payment detail
- approval and evidence review
- proof, release, and receipt visibility
- receipt and reconciliation review

Internal Actenon Cloud team workflow scope:

- deployment health
- log inspection
- database operations
- migration operations
- infrastructure troubleshooting

Those internal operations should not be the customer UI.

## Workflow Conclusion

The minimum invoice payment pilot workflow is operator-driven and trace-driven.

If the repo provides:

- one action queue
- one held and exceptions queue
- one action detail and trace page
- approval and evidence actions
- proof and receipt visibility
- export actions

then the design partner can operate the governed payment flow without requiring a broad platform console.
