# Customer Incident Flow

## Purpose

This document defines how incidents are raised, triaged, and communicated during the managed invoice payment pilot.

It focuses on live pilot operation, not broad enterprise support policy.

## Scope

Use this flow when there is:

- service unavailability
- pilot UI failure
- repeated API errors
- unexpected workflow behavior that looks like a product defect
- hosted environment instability

Do not use this flow for ordinary blocked or held actions that are behaving as designed. Those should start with `EXCEPTION_HANDLING_RUNBOOK.md`.

## Named Contacts

The pilot should operate with at least:

- one customer finance operations owner
- one customer tenant administrator or technical owner
- one provider operations contact
- one provider engineering escalation contact

## First Response Model

### Customer Starts

Customer should raise the issue first when they see:

- a broken screen
- a failing action workflow
- a suspected product defect
- a receipt or trace inconsistency they cannot explain

Minimum information to send:

- time observed
- affected action identifier if known
- screenshot or copied error detail
- `X-Request-ID` if visible
- whether the issue blocks a live invoice payment decision

### Provider Starts

Provider should start the incident flow first when they see:

- runtime outage
- readiness failure
- deployment regression
- database or storage issue
- ingress failure

## Triage Sequence

1. Confirm whether the issue is:
   - workflow exception
   - product defect
   - runtime or infrastructure incident
   - external dependency issue
2. Confirm whether pilot traffic should continue.
3. Identify one named incident owner.
4. Capture the affected identifiers and time window.
5. Use the hosted verification and internal observability docs to narrow the fault.

## Ownership Rules

### Customer Owns First Triage When

- the action is blocked by policy
- the action is waiting for approval
- the action is waiting for evidence
- the business needs to decide whether an exception is acceptable

### Provider Owns First Triage When

- the service is unavailable
- the pilot UI does not load
- the health endpoints fail
- logs show request failures or startup failures
- migrations or deploy steps failed

### Shared Ownership When

- proof issuance failed and the cause is not obvious
- receipt linkage or reconciliation looks inconsistent
- escrow, quarantine, or revoke state raises a real control concern

## Communication Flow

For any real incident:

1. open one shared incident thread or channel
2. state current customer impact
3. state whether pilot traffic is paused or still allowed
4. post status updates on an agreed interval until stable
5. close with one written resolution summary

This is still a named-contact, business-hours pilot support model, not a 24x7 operations program.

## Escalation Path

Escalate from provider operations contact to provider engineering escalation contact when:

- the issue is not understood within the initial review window
- the issue recurs
- the issue affects multiple invoice payment cases
- the issue may indicate data inconsistency or unsafe workflow behavior

Escalate from customer finance owner to customer sponsor when:

- live pilot use must pause
- a policy or operating change is needed
- the issue changes pilot success criteria or scope assumptions

## Closure Criteria

Do not close the incident until:

- the immediate symptom is no longer active
- health checks are green if the incident involved runtime availability
- the customer understands whether any invoice payment action needs follow-up
- the owner has recorded whether the issue was:
  - customer data or business decision
  - customer configuration
  - provider defect or runtime issue
  - external dependency issue

## What This Does Not Claim

- no formal SLA
- no 24x7 pager duty
- no automated incident routing
- no enterprise postmortem workflow tooling

This is the minimum honest incident flow for a managed pilot.
