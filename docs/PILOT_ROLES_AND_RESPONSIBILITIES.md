# Pilot Roles And Responsibilities

## Purpose

This document defines the simplest usable role model for the managed invoice payment pilot.

It distinguishes:

- customer workflow roles
- provider operating roles

It does not claim a full enterprise RBAC product.

## Customer Roles

### Finance Reviewer

Primary purpose:

- inspect invoice payment actions
- understand allow, hold, or block outcomes
- review receipts, reconciliation, and audit trace

Typical access shape:

- `tenant.action_intent.read`
- `tenant.receipt.read`
- `tenant.audit.read`

Closest current system role:

- `audit_viewer`

### Approver

Primary purpose:

- review held approval requests
- inspect rationale and linked evidence
- approve or reject when assigned and permitted

Typical access shape:

- `tenant.action_intent.read`
- `tenant.approval.read`
- `tenant.approval.write`
- often `tenant.evidence.read`

Current product truth:

- this is best represented by a tenant-local custom role or a tightly controlled tenant admin during the pilot
- there is not yet a dedicated built-in system role named `approver`

### Evidence Contributor

Primary purpose:

- resolve missing-evidence cases
- upload evidence
- register external evidence

Typical access shape:

- `tenant.action_intent.read`
- `tenant.evidence.read`
- `tenant.evidence.write`

Current product truth:

- this is also best represented by a tenant-local custom role or a tightly controlled tenant admin during the pilot

### Policy Administrator

Primary purpose:

- manage workflow policy definitions for the pilot tenant

Typical access shape:

- `tenant.policy.read`
- `tenant.policy.write`
- `tenant.action_intent.read`

Current system role:

- `policy_admin`

### Tenant Administrator

Primary purpose:

- manage tenant-local access and configuration
- act as the customer’s operational owner inside the pilot tenant

Typical access shape:

- full tenant-level administrative permissions

Current system role:

- `tenant_admin`

Use carefully in the pilot because it is broader than a pure workflow-review role.

## Provider Roles

### Provider Platform Administrator

Primary purpose:

- bootstrap access
- issue operator and service tokens in the current auth model
- support tenant onboarding and controlled admin changes

Current system role:

- `platform_admin`

This is provider-operated, not a normal customer role.

### Provider Technical Operator

Primary purpose:

- run deployments and migrations
- verify health and readiness
- inspect internal logs
- triage incidents
- support hosted pilot operations

Current product truth:

- this responsibility exists primarily in docs and operational process, not as a customer-facing workflow role

### Service Operator

Primary purpose:

- represent controlled service-to-service actions such as receipt ingestion or lifecycle updates

Current system role:

- `service_operator`

This is best treated as provider-operated or provider-managed integration infrastructure during the pilot.

## Responsibility Split

### Customer Owns

- day-to-day invoice payment review
- approval decisions
- evidence contribution
- policy intent and business rules
- business interpretation of blocked or held actions
- acceptance of pilot workflow outputs

### Provider Owns

- deployment and hosted runtime
- ingress, TLS, secrets, database, and storage operations
- token issuance and access bootstrap in the current auth model
- release execution and rollback handling
- internal observability and incident triage
- support for service-principal and infrastructure-linked workflow paths

## Role Compression For The Pilot

The pilot can run with a very small set of real humans:

- one customer tenant administrator
- one or two customer approvers or finance reviewers
- one provider platform or technical operator

That is enough for a controlled invoice payment pilot if responsibilities are explicit.

## Important Limits

- the product does not yet provide a polished role-management UI
- the product does not yet provide enterprise SSO
- the product does not yet provide a built-in escalation ownership model
- not every workflow role maps to a pre-seeded system role today

Those gaps are acceptable for a managed pilot as long as the operating model is explicit.

The recurring operating rhythm for these roles is defined in:

- `WEEKLY_OPERATIONS_RHYTHM.md`
- `PILOT_REPORTING_CADENCE.md`
- `EXCEPTION_HANDLING_RUNBOOK.md`
