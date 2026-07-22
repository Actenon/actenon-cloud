# Weekly Operations Rhythm

## Purpose

This document defines the default week-to-week operating rhythm for the managed invoice payment pilot.

It gives the customer and provider one practical cadence for:

- held action review
- exception handling
- incident escalation
- change requests
- weekly reporting

## Operating Week Structure

The pilot should run on a simple business-hours rhythm.

## Daily Rhythm

### Customer Daily Responsibilities

- review the held and exceptions queue
- resolve pending approvals where possible
- supply or register missing evidence where possible
- inspect any newly blocked or structurally non-executable actions
- raise an incident if the product or hosted runtime appears broken

### Provider Daily Responsibilities

- verify hosted pilot health during the normal support window
- review internal logs and readiness if there are active issues
- respond to customer-raised incidents or unresolved exceptions
- support controlled token, access, or policy change requests when needed

## Weekly Rhythm

### 1. Early-Week Exception Sweep

Suggested attendees:

- customer finance operations owner
- customer tenant administrator
- provider operations contact

Suggested focus:

- review all open manual follow-up cases
- confirm which held actions are still waiting on customer response
- confirm which blocked actions were intended versus unexpected
- identify any action that needs provider investigation

### 2. Midweek Change Review

Suggested attendees:

- customer tenant administrator
- customer policy owner
- provider implementation owner

Suggested focus:

- requested policy adjustments
- membership or role changes needed for the pilot
- receipt-source or workflow mapping changes
- whether a requested change belongs in the active pilot or should wait

Change requests should stay narrow and traceable. The pilot should avoid uncontrolled scope drift.

### 3. End-Week Operating Review

Suggested attendees:

- customer finance operations owner
- customer approver lead
- provider operations contact

Suggested focus:

- review the weekly operating summary
- review the current pilot success metrics
- review exceptions and incidents from the week
- agree any follow-up actions for the next week

## Incident Rhythm

If there is a real incident:

- switch immediately to the incident flow in `CUSTOMER_INCIDENT_FLOW.md`
- pause normal cadence as needed until the issue is understood
- include the incident summary in the next weekly operating review

## Exception Rhythm

If an action is merely held or blocked as designed:

- keep it in the normal workflow cadence
- do not treat it as a service incident

If an action cannot be resolved through supported workflow actions:

- move it into manual follow-up
- review it in the early-week exception sweep or sooner if time-sensitive

## Reporting Rhythm

The weekly rhythm should produce:

- one weekly operating summary
- one weekly success-metrics review
- one biweekly sponsor-level pilot review

See:

- `PILOT_REPORTING_CADENCE.md`

## Who Owns Resolution

### Customer First

Customer should own first response for:

- approvals
- evidence collection
- intended policy blocks
- business interpretation of receipt mismatches

### Provider First

Provider should own first response for:

- service availability
- readiness failures
- deployment regressions
- migration issues
- hosted runtime and infrastructure issues

### Shared

Customer and provider should jointly resolve:

- unclear proof issuance failures
- unclear reconciliation mismatches
- quarantined or revoked high-sensitivity cases
- change requests that may affect pilot scope or trust posture

## What This Rhythm Does Not Include

- 24x7 support
- formal on-call rotation
- broad self-serve admin operations
- continuous delivery governance

This is the minimum weekly rhythm for a managed pilot, not a mature enterprise operating program.
