# Design Partner Value Hypothesis

## Purpose

This document states the value hypothesis for the invoice payment execution pilot.

It is a hypothesis to test with a serious design partner. It is not a claim of proven customer outcomes.

## Core Hypothesis

If a finance team uses Actenon Cloud as the governed control layer for one outbound invoice payment workflow, then that team should be able to make payment decisions with less ambiguity and better traceability than they can with a fragmented manual process.

## What Value We Expect The Partner To See

### 1. Unsafe Payments Become Easier To Stop Earlier

The partner should be able to block or pause unsafe payment proposals before they move into downstream execution.

Examples include:

- structurally unsafe requests
- wrong-payee or wrong-account situations
- payments that exceed policy thresholds
- payments that are missing required approvals or evidence

### 2. The Review Process Becomes Easier To Explain

The partner should be able to see:

- who requested a payment
- what policy result was produced
- whether approval was required
- whether evidence was required
- whether proof issuance succeeded
- whether release was allowed, held, revoked, or quarantined

This should reduce the need to reconstruct the story across multiple systems.

### 3. Receipt Review Becomes More Useful

The partner should be able to link the receipt or outcome back to the original governed payment decision more directly than in a fragmented process.

That makes exception review and internal audit conversations easier.

### 4. Role Separation Becomes More Visible

The partner should be able to see clearer boundaries between:

- requester
- approver
- release manager
- reviewer

That visibility matters even in a controlled pilot because it shows whether the control model is understandable in practice.

## What Makes The Hypothesis Commercially Credible

This hypothesis is commercially credible because it is based on capabilities already implemented in the repo:

- payment proposal intake
- deterministic policy evaluation
- approval and evidence workflows
- bounded proof issuance
- release-state tracking
- receipt ingestion and audit trace queries

The pilot is not asking the design partner to evaluate a vague future platform concept. It is asking the partner to evaluate a real, narrow workflow.

## What The Hypothesis Is Not

This hypothesis is not:

- a claim of proven ROI
- a claim of production-ready payment execution
- a claim that this repo replaces downstream payment systems
- a claim that proof verification happens inside this repository

Proof verification remains external through a separate verifier repo or verifier interface.

## Evidence That Would Support The Hypothesis

The hypothesis becomes stronger if the pilot demonstrates:

- at least one valid payment allowed and traced end to end
- at least one unsafe payment blocked before execution
- at least one payment paused for missing approval or evidence
- at least one receipt-linked payment trace reviewed successfully by operators
- operator feedback that the decision path is easier to understand than before

## Commercial Interpretation

If the hypothesis is supported, the commercial conclusion is not “the system is production-ready.”

The commercial conclusion is narrower:

This control-plane layer is valuable enough in one invoice payment workflow to justify a deeper production-hardening program.
