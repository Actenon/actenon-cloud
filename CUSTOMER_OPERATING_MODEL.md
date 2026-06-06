# Customer Operating Model

## Purpose

This document defines the live operating model for a managed single-tenant invoice payment pilot.

It is intentionally narrow:

- one customer tenant in active daily use
- one governed invoice payment workflow
- one managed Actenon Cloud deployment operated with provider support

This is not a self-serve cloud operating model.

## Core Principle

Customer operators use the product to review, approve, document, and inspect invoice payment actions.

The provider operates the hosted runtime, deployment path, and pilot support functions around that workflow.

## Customer-Operated Workflow

Customer-side workflow use in the pilot is limited to:

- viewing invoice payment actions
- reviewing held actions
- approving or rejecting when assigned and authorized
- uploading or registering evidence
- reviewing receipts, reconciliation state, and full action trace

These are the daily workflow tasks the pilot is meant to prove.

## Provider-Operated Service Layer

Provider-side operation in the pilot includes:

- deployment and release execution
- TLS, ingress, database, storage, and secret handling
- token issuance and access bootstrap in the current early auth model
- infrastructure troubleshooting
- incident triage
- backup responsibility coordination
- support for policy or membership changes when needed

These are still managed pilot responsibilities, not customer self-service product features.

## Who Can View Actions

The pilot separates action visibility from action authority.

Customer users may view actions if they have tenant-scoped read access, typically through:

- `audit_viewer`
- `policy_admin`
- `tenant_admin`
- a custom tenant role with `tenant.action_intent.read`

The provider may also view actions for support or incident handling through platform-scoped administration or explicitly authorized tenant access.

## Who Can Review Held Actions

Held actions can be inspected by customer users with read access to the tenant workflow state.

Direct in-product review work is most appropriate for:

- finance reviewers
- approvers
- tenant administrators in a controlled pilot

In the current implementation, the review UI is most useful when the user can read:

- action records
- approval state
- evidence state
- audit and receipt traces

## Who Can Approve Or Reject

Approval authority is narrower than visibility.

An approval decision requires both:

1. tenant permission to write approvals
2. a valid approval assignment or otherwise acceptable approval actor for that request

Today, the strongest built-in path is:

- a customer user with tenant permission `tenant.approval.write`
- plus an approval request that allows that principal to decide

That means approval authority is not just "can open the action." It is a combination of role-based access and workflow assignment.

## Who Can Upload Or Register Evidence

Customer users can resolve missing-evidence cases when they have:

- `tenant.evidence.write`

This allows:

- evidence upload
- external evidence registration

Evidence review is still weaker than a finished enterprise product because browser-safe evidence retrieval is not fully implemented yet.

## Who Can Change Policy

Policy changes are administrative, not part of the day-to-day payment review loop.

In the current backend, policy changes should be limited to:

- customer `policy_admin`
- customer `tenant_admin`
- provider support acting under explicit customer direction where needed

The current pilot does not require a polished customer policy-authoring UI. Policy management can remain API-driven and controlled.

## Who Can Change Tenant Access

Tenant access changes are also administrative.

In the current backend, they should be limited to:

- customer `tenant_admin`
- provider support or provider platform admin during bootstrap and pilot support

Because auth is still early, bootstrap and token issuance remain provider-operated even when tenant membership records exist.

## Escalation And Follow-Up

The pilot does not yet implement a full in-product escalation system with ownership, SLA timers, or routed queues.

So "escalate" in the live pilot means:

- identify the action as manual follow-up
- export or review the trace
- move the case through the agreed customer and provider operating process outside the product

This is a real operating-model boundary, not a missing UI label.

## Observability Access Versus Action Authority

The most important operating boundary is:

- some users only need to observe
- fewer users should be able to approve or alter workflow state

For the pilot:

- customer finance reviewers and auditors should be able to inspect the trace without gaining action authority
- customer approvers should only receive the narrow authority needed for approval decisions
- customer policy administrators should not automatically receive runtime infrastructure authority
- provider operators may need infrastructure and support access without becoming normal customer approvers

## Current Pilot Truth

The live pilot operating model is credible, but still managed:

- customer operators can use the workflow surface
- provider operators still own hosting and deployment operations
- early auth means token issuance and some access bootstrap remain provider-assisted
- proof verification remains external through a separate verifier repo or verifier interface

That is appropriate for a pilot-ready managed deployment infrastructure posture.

For the recurring live cadence around these roles, use:

- `EXCEPTION_HANDLING_RUNBOOK.md`
- `CUSTOMER_INCIDENT_FLOW.md`
- `PILOT_REPORTING_CADENCE.md`
- `WEEKLY_OPERATIONS_RHYTHM.md`
