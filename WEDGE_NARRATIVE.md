# Wedge Narrative

## Purpose

This document explains the wedge narrative for Actenon Cloud in plain commercial terms.

It is specific to the chosen first wedge: outbound invoice payment execution.

## The Narrative In One Sentence

Start with one painful, review-heavy invoice payment workflow and make it safer, clearer, and easier to trace before trying to sell a broader control-plane story.

## Why This Wedge Works

Invoice payment execution is the right first wedge because it is:

- narrow enough to pilot without broad process redesign
- important enough for finance leaders to care about
- measurable through blocked actions, approval visibility, and receipt traceability
- already supported by the implemented workflow in this repo

It is easier to sell honestly than a broad claim about generalized automation or autonomous execution.

## The Before And After Story

### Before

An invoice payment may move through a scattered path:

- someone proposes payment details in one system
- approval happens in email, chat, or a separate tool
- evidence is stored somewhere else
- release decisions are not clearly recorded
- the receipt arrives later with weak linkage back to the original decision

The main business problem is not only speed. It is that the control path is fragmented and difficult to explain.

### After In The Pilot

For one narrow invoice payment workflow:

- the payment proposal enters a governed control path
- explicit policy decides whether the payment is allowed, denied, or requires more control steps
- approvals and evidence are attached to the same decision path
- a bounded proof is issued for the exact governed payment
- release state is visible
- the resulting receipt is linked back into one searchable trace

The pilot does not claim finished automation. It claims a clearer and safer governed decision path.

## Why This Wedge Is Commercially Credible

This wedge is commercially credible for three reasons.

### 1. It matches current implementation reality

The repo already supports the control-plane workflow around invoice payment execution.

### 2. It solves a buyer-recognizable pain

Finance buyers can understand the pain of unclear payment review, scattered approvals, and weak traceability without needing to buy into a broad platform thesis first.

### 3. It creates a measurable pilot

The partner can judge the pilot through:

- blocked unsafe payments
- visible approval and evidence handling
- time to safe decision
- receipt-linked audit traces

This wedge also supports a clean pilot-stage commercial model: a fixed pilot or setup fee for workflow mapping, configuration, and supervised delivery now, then usage tied to proved and allowed consequential actions later if the pilot proves value. Blocked actions stay off the usage bill to preserve trust.

## Why This Wedge Comes Before Broader Expansion

Starting here is commercially stronger than trying to sell:

- refunds first
- batch payments first
- broad treasury workflows first
- generalized finance automation first

Those paths would introduce more integration surface, more edge cases, and more narrative sprawl before the design partner has seen value from one clear workflow.

## Long-Term Platform Potential Versus Pilot Value

The pilot value is immediate and narrow:

- safer invoice payment decisions
- clearer role separation
- better traceability from proposal to receipt

The long-term platform potential is broader, but it should stay a second conversation.

The correct sequence is:

1. prove value in one invoice payment workflow
2. confirm the control model is operationally useful
3. decide whether production hardening and broader workflow expansion are justified

## Boundary Note

The wedge narrative does not change repo boundaries:

- this repo is the control plane
- the open kernel remains separate
- proof verification remains available through a separate verifier repo or verifier interface

Those boundaries matter for technical truth, but the commercial story should lead with the payment-control problem, not with dependency structure.

## Narrative Close

The first wedge is not “buy a new platform.”

The first wedge is:

Take one outbound invoice payment workflow that is painful to review and hard to trace, and show that a dedicated control plane can make it more understandable and more governable.
