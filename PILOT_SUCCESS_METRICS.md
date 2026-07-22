# Pilot Success Metrics

## Purpose

This document defines how the invoice payment execution pilot should be judged.

These are pilot targets and evaluation measures, not claimed results.

## Core Success Question

Does Actenon Cloud make invoice payment execution safer, clearer, and easier to audit for one design partner without pretending the current repo is already production-hardened?

## Required Validation Events

The pilot should demonstrate all of the following at least once:

- one valid invoice payment allowed and traced end to end
- one invoice payment blocked by policy
- one invoice payment requiring evidence before progress
- one invoice payment requiring approval before progress
- one receipt-linked payment trace with reconciliation output

## Safety Metrics

- count of invalid or unsafe payment proposals blocked before execution
- count of duplicate submissions safely deduplicated by idempotency
- count of wrong-payee or structurally unsafe requests blocked before release
- count of payments that could not be issued because required approvals or evidence were missing

## Workflow Metrics

- time from intake to safe decision
- time from approval request creation to approval satisfaction
- percentage of pilot payments with complete approval visibility
- percentage of pilot payments with complete evidence linkage when required

## Trace And Receipt Metrics

- percentage of pilot payments with a receipt linked back to the Action Intent
- percentage of pilot payments with proof, escrow, and receipt all visible in one audit trace
- number of receipt mismatches caught by reconciliation
- usefulness of the audit trace in operator review sessions

## Commercial Success Indicators

- reduced manual ambiguity during payment review
- clearer separation of requester, approver, and release roles
- operator confidence that the system explains why a payment was allowed or refused
- partner willingness to move from pilot to production-hardening work

## Suggested Sign-Off Criteria

- the partner agrees the pilot solved a real invoice payment control problem
- the partner can review at least one complete trace without needing multiple external systems
- the partner confirms the current limitations are understood and acceptable for pilot scope
- the partner can identify what hardening work would be required for broader rollout
