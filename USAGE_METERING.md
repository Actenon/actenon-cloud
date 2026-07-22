# Usage Metering

## Purpose

This document defines the current usage-metering model for Actenon Cloud.

It is intentionally narrow. It supports pilot reporting, internal commercial analysis, and later per-action pricing design. It does not implement billing, invoicing, collections, or entitlement enforcement.

## Current Metering Posture

The repo now exposes tenant-scoped usage summaries for the invoice payment pilot.

Current status:

- metering is implemented
- reporting is implemented
- billing is not implemented

The point of this surface is to make usage truth visible before building a broader billing stack.

## Meter Definitions

### Billable Candidate Metric

`billable_proved_and_allowed_actions`

Definition:

- distinct Action Intents
- within one tenant
- within the selected reporting period
- where the first successful proof issuance happened in that reporting period

This is the current future pricing candidate because it reflects a governed action that progressed through the control path far enough to be proved.

This is not a live invoice line-item yet.

### Non-Billable Prevention Metric

`blocked_or_refused_actions`

Definition:

- distinct Action Intents
- created in the selected reporting period
- with final intake outcomes of `deny` or `structurally_non_executable`

These counts matter for pilot ROI and trust discussions, but they are not treated as billable usage.

### Supporting Pilot Metrics

The usage summary also exposes:

- `submitted_actions`
- `held_for_review_actions`
- `reviewed_actions`
- `receipt_linked_actions`
- split of `blocked_policy_actions` versus `structurally_refused_actions`

These metrics help explain operator effort, workflow completion, and prevention value during a pilot.

## Reporting API

Current reporting surface:

- `GET /api/v1/usage/summary`

Main query parameters:

- `tenant_id`
- `workflow_key`
- `period_start`
- `period_end`

If no period is supplied, the report defaults to the current UTC month to date.

If a custom period is supplied, both `period_start` and `period_end` must be provided together.

## Reporting Semantics

The report intentionally uses different event timestamps for different questions:

- submitted, blocked, and held counts use Action Intent `created_at`
- billable candidate counts use the first successful proof event time
- reviewed counts use the first approval decision or evidence submission time
- receipt-linked counts use the first linked receipt time

This keeps the output useful for both pilot reporting and future pricing design without pretending all categories share the same billing event.

## Pilot UI Hook

The pilot action list now shows a small usage card for the current reporting period so operators and customer stakeholders can see:

- submitted actions
- proved and allowed actions
- blocked or refused actions
- reviewed actions
- receipt-linked actions

The card explicitly states that the surface is metering only and that blocked or refused actions are not usage-billed.

## What This Does Not Do Yet

This repo still does not implement:

- invoices
- Stripe or payment collection for usage
- contract billing rules
- customer billing accounts
- credit balances
- disputes or revenue recognition
- a general-purpose billing admin console

Those should remain out of scope until the usage definition itself is validated in pilots.
