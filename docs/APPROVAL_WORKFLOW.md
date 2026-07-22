# Approval Workflow

## Purpose

This document defines the first real approval workflow engine in Actenon Cloud.

The goal is not to model every enterprise approval variant yet. The goal is to provide a production-shaped minimum for finance actions that need durable approval requests, approver assignment, separation of duties, expiry, and immutable decision records.

## Boundary

The approval engine is control-plane logic.

It does not replace kernel execution semantics, receipt semantics, or proof semantics. It only determines whether a tenant-governed Action Intent has satisfied the local human or service approval conditions required before later downstream execution or proof workflows may continue.

## Current Endpoints

- `GET /api/v1/approvals`
- `GET /api/v1/approvals/{approval_request_id}`
- `POST /api/v1/approvals/{approval_request_id}/decisions`

Approval requests are currently created automatically during Action Intent intake when policy evaluation yields an `approval_requirement` snapshot or an `approval_required` decision.

## Current Model

### `ApprovalRequest`

The current request model stores:

- tenant scope
- linked `action_intent_record_id`
- generating `policy_id` and `workflow_rule_id` if present
- `approval_group_key`
- `required_decision_count`
- `eligible_role_ids`
- separation-of-duties settings
- current status
- optional expiry timestamp
- terminal timestamps for satisfaction or rejection

### `ApproverAssignment`

Assignments make approver targeting explicit.

Release 1 supports:

- principal assignment through `eligible_principal_ids`
- role eligibility through `eligible_role_ids`

Concrete tenant role resolution is not implemented yet. For now, role-based approval is a contract surface on the API and policy layer, while principal assignments are the strongest currently enforced assignment path.

### `ApprovalDecision`

Decisions are immutable records. Each decision stores:

- deciding principal type and identifier
- `approve` or `reject`
- optional reason
- cited `evidence_object_ids`
- creation timestamp

One principal may only decide once per approval request.

## Policy Binding

The policy engine now supports an optional `approval_requirement` object on each rule. The current shape is:

- `required_decision_count`
- `eligible_principal_ids`
- `eligible_role_ids`
- `approval_group_key`
- `expires_in_seconds`
- `require_requester_separation`
- `require_distinct_approvers`

If a rule returns `approval_required` without an explicit requirement object, the service creates a minimal default requirement:

- one required approval
- no preassigned principals
- requester separation enabled
- distinct approvers enabled

## Status Transitions

The current request status machine is:

- `pending`
- `satisfied`
- `rejected`
- `expired`
- `canceled`

Current transition behavior:

- intake creates `pending` requests
- an `approve` decision increments the satisfied count
- once the required decision count is met, the request becomes `satisfied`
- a single `reject` decision makes the request `rejected`
- passing `expires_at` moves a pending request to `expired`

The linked Action Intent stores an aggregate `approval_state`:

- `not_started`
- `not_required`
- `pending`
- `satisfied`
- `rejected`
- `expired`
- `canceled`

## Separation Of Duties

Release 1 enforces the most important finance control that is feasible with the current identity scope:

- when `require_requester_separation=true`, the original requester cannot satisfy the approval request

The engine also prevents duplicate approval by the same principal on the same request.

More advanced segregation rules such as manager chains, legal-entity restrictions, and cross-team quorum policies are deferred.

## What Is In Scope Now

- one or more approval requests linked to an Action Intent
- assigned approver principals
- optional role eligibility hints
- immutable approval or rejection decisions
- request expiry
- aggregate Action Intent approval state
- evidence citation on approval decisions

## What Is Deferred

- multi-stage workflow graphs
- delegation and out-of-office reassignment
- escalations, reminders, and SLA timers
- identity-provider-backed user and role administration
- parallel approval groups with conditional branching
- approval-based proof issuance
- enterprise admin UI
