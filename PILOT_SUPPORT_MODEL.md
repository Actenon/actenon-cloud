# Pilot Support Model

## Purpose

This document defines the recommended support model for the invoice payment execution pilot.

## Named Roles

Recommended customer-side roles:

- pilot sponsor
- technical owner
- finance operations owner
- approver lead

Recommended Actenon Cloud roles:

- engineering lead
- implementation owner
- operations contact

## Support Posture

This pilot should be run with a named-contact, business-hours support model.

The pilot does not imply:

- 24x7 support
- formal production SLA
- fully automated incident response

## Recommended Cadence

- kickoff session
- onboarding working sessions during setup
- regular pilot review cadence
- explicit exception review after any blocked, revoked, quarantined, or mismatched receipt case

Supporting live-ops docs:

- `EXCEPTION_HANDLING_RUNBOOK.md`
- `CUSTOMER_INCIDENT_FLOW.md`
- `PILOT_REPORTING_CADENCE.md`
- `WEEKLY_OPERATIONS_RHYTHM.md`

## Triage Model

Primary pilot issue classes:

- intake or policy issue
- approval or evidence issue
- proof issuance issue
- escrow or execution-state issue
- receipt ingestion or reconciliation issue

Recommended first action:

- locate the `action_intent_record_id`
- review the audit trace
- determine whether the issue belongs to customer data, control-plane behavior, or the downstream execution process

## Customer Responsibilities In Support

- provide named operators for pilot activities
- provide receipt and downstream execution contacts
- confirm when exceptions reflect intended policy versus configuration error
- supply example invoice and payment scenarios during validation

## Actenon Cloud Responsibilities In Support

- maintain the pilot environment
- help configure policy and workflow rules
- review exceptions and trace data
- document known limits and next-step hardening recommendations
