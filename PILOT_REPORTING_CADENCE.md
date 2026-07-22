# Pilot Reporting Cadence

## Purpose

This document defines what the customer should see regularly during the managed invoice payment pilot.

The goal is to make the pilot feel controlled, legible, and measurable without pretending it is already a production operations program.

## Reporting Layers

The pilot should use three reporting layers:

- weekly operating summary
- weekly success-metrics review
- periodic sponsor or pilot review

## 1. Weekly Operating Summary

Audience:

- customer finance operations owner
- customer tenant administrator
- provider operations contact

Suggested cadence:

- once per week during active pilot weeks

Suggested contents:

- count of invoice payment actions submitted
- count allowed
- count held for approval
- count held for evidence
- count blocked by policy
- count structurally non-executable
- count of receipt-linked actions
- count of manual follow-up cases still open
- short note on any runtime or workflow incidents

This is the main trust-building report for day-to-day pilot operation.

## 2. Weekly Success-Metrics Review

Audience:

- customer finance operations owner
- customer approver lead
- provider implementation owner

Suggested cadence:

- once per week, usually together with or immediately after the weekly operating summary

Metrics to review should come directly from `PILOT_SUCCESS_METRICS.md`, especially:

- time from intake to safe decision
- time from approval request creation to approval satisfaction
- count of invalid or unsafe proposals blocked before execution
- percentage of pilot payments with complete approval visibility
- percentage of pilot payments with complete evidence linkage when required
- percentage of pilot payments with receipt linkage
- usefulness of the audit trace in real operator review

The weekly review should keep the discussion tied to observed pilot cases, not abstract product claims.

## 3. Pilot Review Cadence

Audience:

- customer sponsor
- customer finance operations owner
- customer technical owner
- provider implementation owner
- provider engineering lead when needed

Suggested cadence:

- every two weeks during the pilot
- plus one final exit review

Suggested contents:

- what worked well
- what exceptions occurred
- whether customer operators trust the workflow more
- whether policy, approval, and evidence rules need adjustment
- whether the pilot is still inside the agreed scope
- whether the success case for production hardening is becoming clearer

## Incident Reporting

Do not wait for the weekly review if there is:

- runtime outage
- repeated workflow failure
- receipt mismatch with financial significance
- a pilot pause decision

Those should use `CUSTOMER_INCIDENT_FLOW.md` and then be summarized in the next weekly report.

## What The Customer Should See Regularly

At minimum, the customer should receive:

- one weekly operating summary
- one weekly success-metrics review
- one periodic sponsor-level pilot review
- immediate communication for material incidents

## What This Reporting Does Not Yet Claim

- no automated customer dashboard distribution
- no executive BI layer
- no formal board-style reporting pack

This cadence is intentionally simple and pilot-appropriate.
