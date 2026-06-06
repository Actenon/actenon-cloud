# Access And Approval Boundaries

## Purpose

This document defines the minimum access and approval boundaries for the managed invoice payment pilot.

The goal is simple:

- make observability broad enough for review
- keep action authority narrow enough for trust

## Boundary 1: Seeing An Action Is Not The Same As Acting On It

A user may be allowed to:

- open the invoice payment queue
- inspect action detail
- inspect receipts and trace exports

without being allowed to:

- approve
- reject
- upload evidence
- change policy

This is the core control boundary for the pilot.

## Boundary 2: Approval Requires Both Permission And Workflow Eligibility

Approval is allowed only when both conditions are true:

1. the session has tenant approval write authority
2. the approval request still accepts that actor under the workflow rules

That means an operator cannot approve merely because they are a broad tenant reader.

It also means a broad tenant administrator still should not act as a casual approver without explicit pilot agreement.

## Boundary 3: Blocked Actions Are Visible But Not Reversible In Product

Blocked actions should remain easy to inspect.

But the current pilot UI does not expose an override path for:

- policy-denied outcomes
- structurally blocked outcomes

That is intentional. Visibility exists; reversal authority does not.

## Boundary 4: Held Actions Divide Into Reviewable And Manual Follow-Up

Held actions are not all the same.

Some held actions are immediately reviewable in product:

- pending approval
- missing evidence

Others still require manual follow-up outside the current workflow controls:

- expired approval with no reopen path
- proof failure with no in-product recovery path
- receipt mismatch or reconciliation that needs manual review

The product must keep these distinct so operators do not mistake manual follow-up for supported in-product resolution.

## Boundary 5: Policy Administration Is Separate From Payment Review

Policy changes should not be treated like ordinary payment operations.

For the pilot:

- reviewing invoice payment actions is a customer workflow function
- editing policy is an administrative function

So policy authority should stay with:

- `policy_admin`
- `tenant_admin`
- provider support acting under customer direction when necessary

It should not automatically be bundled into finance reviewer or approver access.

## Boundary 6: Infrastructure Access Is Provider-Operated

Customer operators do not need direct access to:

- deployment tooling
- migration tooling
- ingress configuration
- database operations
- central log collection plumbing
- hosted secret handling

Those remain provider-operated in the pilot.

## Boundary 7: Escalation Is Operational, Not Yet Productized

The pilot does not yet implement:

- persisted operator notes
- escalation ownership
- in-product follow-up queues with SLA routing

So escalation currently means:

- identify the case as follow-up
- use trace and audit exports if needed
- hand off through the managed pilot support process

That boundary should be stated clearly to customer operators.

## Boundary 8: Proof Verification Is External

This repo may issue and track proofs, but proof verification remains external through a separate verifier repo or verifier interface.

So approval or operational decisions in this repo must not be described as built-in verifier behavior.

## Recommended Minimum Access Shape For The Pilot

### Read-Only Workflow Visibility

Use for:

- finance reviewers
- audit reviewers

Minimum permissions:

- `tenant.action_intent.read`
- `tenant.receipt.read`
- `tenant.audit.read`

### Approval Authority

Use for:

- assigned approvers

Minimum permissions:

- `tenant.action_intent.read`
- `tenant.approval.read`
- `tenant.approval.write`

### Evidence Resolution

Use for:

- operators responsible for missing evidence

Minimum permissions:

- `tenant.action_intent.read`
- `tenant.evidence.read`
- `tenant.evidence.write`

### Policy Administration

Use for:

- customer policy owners

Minimum permissions:

- `tenant.policy.read`
- `tenant.policy.write`
- `tenant.action_intent.read`

## Current Gap To Keep In Mind

The current seeded role set is helpful but not complete for workflow separation.

In particular:

- `audit_viewer` cleanly supports read-only visibility
- `policy_admin` cleanly supports policy control
- `tenant_admin` is broader than ideal for routine approval work
- dedicated approver and evidence-contributor roles are best represented today as tenant-local custom roles rather than built-in system roles

That is acceptable for a managed pilot, but it should be said explicitly.
