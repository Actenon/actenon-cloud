# Pilot Wedge Justification

## Purpose

This document explains why invoice payment execution is the right first design-partner wedge for Actenon Cloud.

It separates technical truth from commercial justification and keeps the separate open kernel and separate verifier boundary intact.

## Decision

The right first wedge is outbound invoice payment execution.

This remains the preferred wedge unless the underlying implementation reality changes materially.

## Why Invoice Payment Execution Is The Right First Wedge

### 1. The current contract reality supports it

The pinned finance Action Intent contract used by this repo already supports:

- `action_type = "payment"`

That makes invoice payment execution a supported and honest fit for the current implementation.

### 2. The implemented workflow already supports it

The current repo already implements the core control-plane workflow needed around invoice payment execution:

- intake
- deterministic policy evaluation
- approval workflow
- evidence collection
- bounded proof issuance
- capability escrow lifecycle tracking
- receipt ingestion
- reconciliation and audit traces

This is enough to package a serious pilot around one narrow workflow without pretending broader maturity than the repo actually has.

### 3. The buyer problem is easy to understand

Outbound invoice payment review is a concrete finance control problem.

A design partner can quickly understand the value of:

- blocking unsafe payments before execution
- requiring approvals or evidence for higher-risk payments
- recording exactly why execution was allowed or refused
- connecting the receipt back to the original governed decision

### 4. The workflow stays commercially narrow

Invoice payment execution can be scoped to:

- one tenant
- one workflow family
- one payment per request
- one clear set of operators and controls

That makes pilot setup, pilot success criteria, and pilot limits easier to explain.

### 5. The repo can stay honest about simulation boundaries

The current repo can support a meaningful invoice-payment governance pilot even though:

- capability release is still simulated
- signing is still early
- auth is still early
- observability is still limited

That is commercially acceptable for a controlled pilot because the core value being tested is governance, traceability, and safe release decision-making around invoice payment execution.

## Why Refund Execution Is Not The Better First Wedge

Refund execution is not the better first wedge today because:

- it is not a first-class `action_type` in the current pinned kernel finance contract used by this repo
- packaging it first would require a less direct story than invoice payment execution
- it would weaken the alignment between the repo's implemented path and the pilot story

Refunds may still be a future wedge, but they are not the strongest honest starting point in the current repository state.

## Why Broader Finance Workflows Are Not The Right First Wedge

The following are intentionally not better starting wedges for the current pilot:

- batch payments
- payout orchestration
- payroll
- treasury movement workflows
- vendor onboarding
- generalized finance automation

These options would broaden scope, increase integration burden, and reduce the clarity of the pilot offer.

## Separate Kernel And Verifier Boundary

This wedge does not change the system boundary:

- the open kernel remains a separate external dependency for canonical contracts and execution-side semantics
- proof verification remains provided through a separate external verifier repo or verifier interface
- Actenon Cloud remains the commercial layer that governs, records, and orchestrates around those external interfaces

The pilot should never describe this repository as the verifier.

## Commercial Justification

Invoice payment execution is the right first wedge because it gives a serious design partner a clear yes-or-no commercial question:

Would a dedicated control plane make outbound invoice payment execution safer, easier to review, and easier to audit for this workflow?

That question is more commercially actionable than a broad platform pitch because it can be tested with:

- a small number of users
- a small number of payment scenarios
- controlled environment setup
- visible trace outputs

## Conditions That Must Stay True

This wedge remains the right first wedge only if the following stay true:

- the pilot remains narrowly scoped
- the repo continues to present simulated components honestly
- the separate kernel and verifier boundaries remain explicit
- no broader workflow claims are introduced ahead of implementation reality

## Conclusion

Invoice payment execution is the strongest first wedge because it is the best intersection of:

- current contract support
- implemented control-plane capability
- buyer legibility
- pilot controllability
- honest commercial positioning

That makes it the right basis for the next GTM passes.
