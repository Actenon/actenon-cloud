# Policy Management API

## Purpose

This document defines the first tenant and workflow policy management APIs for Actenon Cloud.

## Scope

The current scope is intentionally backend-first and finance-focused:

- minimal tenant creation and retrieval
- versioned workflow policy management
- deterministic rule evaluation inputs for Action Intent intake

This pass does not build a policy UI.

## Endpoints

### Tenant Prerequisites

#### `POST /api/v1/tenants`

Creates a tenant record used by policy management and Action Intent intake.

#### `GET /api/v1/tenants`

Lists tenants.

#### `GET /api/v1/tenants/{tenant_id}`

Fetches one tenant.

### Policy Management

#### `POST /api/v1/policies`

Creates a new draft policy version for a tenant and workflow.

#### `GET /api/v1/policies`

Lists policies, optionally filtered by `tenant_id`, `workflow_key`, or `status`.

#### `GET /api/v1/policies/{policy_id}`

Fetches a single policy.

#### `PUT /api/v1/policies/{policy_id}`

Updates a draft policy. Active or retired policies are immutable through this endpoint.

#### `POST /api/v1/policies/{policy_id}/activate`

Activates a policy version. Any previously active policy for the same tenant and workflow is retired automatically.

## Policy Shape

Each policy is tenant-scoped and workflow-scoped. It contains:

- `tenant_id`
- `workflow_key`
- `name`
- `description`
- `finance_action_classes`
- `default_decision`
- ordered `rules`

## Rule Model

Each rule is explicit and deterministic:

- `rule_id`
- `priority`
- `decision`
- `all_conditions`
- optional `approval_requirement`
- optional `evidence_requirement`

Supported condition sources:

- `action_intent`
- `context`
- `intake`

Supported operators:

- `equals`
- `not_equals`
- `gte`
- `gt`
- `lte`
- `lt`
- `in`
- `contains`
- `exists`

Rule evaluation is ordered by ascending `priority`, then by the stored rule order within the policy. The first matching rule wins.

## Approval And Evidence Requirements

Rules may now include explicit workflow requirement snapshots.

Current `approval_requirement` fields:

- `required_decision_count`
- `eligible_principal_ids`
- `eligible_role_ids`
- `approval_group_key`
- `expires_in_seconds`
- `require_requester_separation`
- `require_distinct_approvers`

Current `evidence_requirement` fields:

- `minimum_count`
- `allowed_evidence_types`
- `expires_in_seconds`

This keeps finance workflow behavior explicit and reviewable without introducing a separate approval UI or a programmable policy runtime.

## Dynamic Context Inputs

The system supports dynamic context conceptually through `evaluation_context` on the intake API. Policy rules can refer to context fields such as:

- `risk_tier`
- `evidence_present`
- request channel or operator-provided routing signals

This keeps policy deterministic without embedding code execution in policies.

## Default Decision

If no rule matches, the policy’s `default_decision` is used.

If no active policy exists for the tenant and workflow, the intake path currently returns `deny`.

## Finance-Focused Release 1 Posture

Policy management is centered on finance actions such as:

- payments
- transfers
- payouts
- collections
- settlement instructions

Policies should stay explicit and reviewable. The current design favors JSON rule documents over a more complex expression language or UI builder.
