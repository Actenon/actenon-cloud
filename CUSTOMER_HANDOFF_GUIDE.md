# Customer Handoff Guide

## Purpose

This guide explains what a design partner receives in the current Actenon Cloud pilot and how the managed invoice payment workflow is expected to run in practice.

It is written for the customer team, not only for the internal implementation team.

## What This Pilot Is

This pilot gives the customer one governed outbound invoice payment workflow inside Actenon Cloud.

The pilot lets the customer:

- submit or inspect invoice payment actions
- see whether each action is allowed, held for review, or refused
- complete approval and evidence steps when required
- inspect proof, receipt, and full trace progression
- review period usage and workflow activity during the pilot

This is a managed pilot. It is not a self-serve product rollout.

## What The Customer Team Will Use

The main customer-facing surfaces are:

- the invoice payment action list
- the held and review queue
- the action detail and trace view
- approval and evidence actions where supported
- trace export
- usage reporting for the current pilot reporting period

## What The Provider Runs

The provider operates the hosted pilot environment, including:

- deployment and releases
- database and evidence-storage setup
- TLS, ingress, and secrets
- operator bootstrap in the current auth model
- internal monitoring, log review, and incident triage
- support for policy, mapping, or access adjustments during the pilot

This remains provider-operated because the current product is still pilot-stage.

## What The Customer Owns

The customer owns the workflow operation and business decisions:

- day-to-day held-action review
- approval or decline decisions where assigned
- evidence submission or registration where required
- interpretation of blocked or refused outcomes
- downstream execution contacts and receipt-process inputs
- participation in weekly operating and sponsor reviews

## What The Customer Must Provide Before Go-Live

The customer should provide:

- one finance or pilot sponsor
- one operations owner
- one technical owner or tenant administrator
- one clearly defined invoice payment workflow
- approval rules and evidence expectations
- source-system and receipt-process contacts
- a named set of approvers or reviewers

## What The Customer Should Expect Week To Week

The normal pilot rhythm is:

- daily held and exceptions review by the customer operations team
- one weekly operating review
- one weekly metrics and usage review
- one biweekly sponsor review
- immediate communication if there is a real hosted-pilot incident

## How Usage And Value Are Measured

During the pilot, Actenon Cloud reports workflow activity for the customer tenant, including:

- submitted actions
- proved and allowed actions
- blocked or refused actions
- reviewed actions
- receipt-linked actions

These numbers are used for:

- weekly pilot reporting
- operator and sponsor trust discussions
- ROI and workflow-value discussion
- future per-action pricing design if the pilot succeeds

Important current truth:

- this is metering only, not customer billing
- blocked or refused actions are visible because they show prevention value
- blocked or refused actions are not treated as usage-billed actions

## What Happens When An Action Is Held Or Refused

### Held For Review

If an action is held for approval or evidence:

- the customer reviews it in the product
- the customer resolves the missing control step where possible
- the provider helps when the issue appears to be workflow configuration or runtime behavior

### Refused

If an action is refused by policy or structure:

- the customer can inspect the action and trace
- the customer should not expect a general in-product override path
- the customer and provider can review whether the refusal reflects intended policy or a configuration issue

### Manual Follow-Up

Some cases still require follow-up outside the product, including certain proof failures, expired approvals, or reconciliation exceptions.

That is part of the current pilot truth.

## How To Ask For Changes

Changes during the pilot should stay narrow and explicit.

Typical change requests are:

- policy tuning
- approver or access changes
- mapping adjustments
- receipt-source adjustments

The customer should route these through the named operations owner or technical owner and review them with the provider in the regular pilot cadence.

## Current Limitation Disclosures

The customer team should understand the following before kickoff:

- the pilot covers one invoice payment workflow, not a broad finance platform
- hosting is managed and single-tenant
- auth is still early and may require provider-assisted bootstrap
- signing is still early and uses the current development-local path unless upgraded separately
- uploaded evidence is currently filesystem-backed
- capability release remains simulated in the current repo
- proof verification remains outside this repo through a separate verifier boundary
- observability is pilot-grade rather than a full enterprise monitoring stack

This pilot is for design-partner validation. It is not a production-readiness claim.

## Best Next Docs

After this guide, the customer team should read:

- [LIVE_PILOT_OVERVIEW.md](LIVE_PILOT_OVERVIEW.md)
- [DEPLOYMENT_AND_OPERATIONS_INDEX.md](DEPLOYMENT_AND_OPERATIONS_INDEX.md)
- [CUSTOMER_OPERATING_MODEL.md](CUSTOMER_OPERATING_MODEL.md)
- [PILOT_REPORTING_CADENCE.md](PILOT_REPORTING_CADENCE.md)
- [USAGE_METERING.md](USAGE_METERING.md)
- [PILOT_LIMITATIONS.md](PILOT_LIMITATIONS.md)
