# Design Partner Conversation Flow

## Purpose

This document defines the recommended flow for early design-partner conversations about the invoice payment execution pilot.

It is not a polished script. It is a practical conversation sequence that keeps the commercial story aligned to current pilot truth.

## Conversation Goal

The goal of the first design-partner conversation is not to close a production deployment.

The goal is to determine whether the prospect has a real invoice payment control problem and whether the current pilot wedge is a credible fit.

## Step 1: Start With The Buyer Problem

Primary message:

- invoice payments are often difficult to review, difficult to explain, and difficult to trace from proposal to receipt

Supporting assets:

- `BUYER_PROBLEM.md`
- `WEDGE_NARRATIVE.md`

What to learn:

- whether this pain is real for the prospect
- whether the problem is important enough to justify pilot attention

## Step 2: Narrow To The Wedge

Primary message:

- the first wedge is one outbound invoice payment workflow, not broad finance automation

Supporting assets:

- `WEDGE_NARRATIVE.md`
- `PILOT_SCOPE_AND_BOUNDARIES.md`
- `PILOT_EXECUTIVE_BRIEF.md`

What to learn:

- whether the prospect can keep scope narrow
- whether the prospect actually wants this wedge or is really asking for a broader system

## Step 3: Explain The Value Hypothesis

Primary message:

- the pilot tests whether a dedicated control plane can reduce ambiguity and improve traceability around invoice payment decisions

Supporting assets:

- `DESIGN_PARTNER_VALUE_HYPOTHESIS.md`
- `PILOT_SUCCESS_METRICS.md`

What to learn:

- whether the buyer values blocked unsafe payments, clearer approvals, and better receipt traceability
- whether the buyer accepts a measurable pilot rather than a broad promise

## Step 4: Explain What The Pilot Actually Does

Primary message:

- Actenon Cloud governs the payment decision path before execution and records the resulting trace

Supporting assets:

- `DESIGN_PARTNER_PILOT_OVERVIEW.md`
- `PILOT_OPERATOR_JOURNEY.md`
- `PILOT_ARCHITECTURE.md`

What to learn:

- whether the prospect understands the operating model
- whether the prospect has the upstream and downstream systems needed for the pilot

## Step 5: State The Boundaries And Limitations Early

Primary message:

- this is a controlled pilot, not a production-readiness claim

Supporting assets:

- `PILOT_LIMITATIONS.md`
- `CONTROL_PLANE_RELEASE_READINESS.md`
- `BLOCKERS.md`
- `PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md`

Key points to state clearly:

- capability release is still simulated
- auth is still early
- signing is still early
- proof verification is external through a separate verifier repo or verifier interface

What to learn:

- whether the prospect can accept the simulation and readiness boundaries

## Step 6: Qualify For Pilot Fit

Primary message:

- only run the pilot if the prospect has the right workflow, team, and tolerance for a controlled pilot

Current supporting assets:

- `COMMERCIAL_BASELINE.md`
- `GTM_WORKING_ASSUMPTIONS.md`

Still-needed asset:

- design-partner qualification rubric

What to learn:

- whether there is a finance sponsor
- whether there is a technical owner
- whether there is a real invoice payment workflow in scope
- whether the prospect can support a time-boxed pilot

## Step 7: Move To Pilot Offer And Proposal Only After Fit

Primary message:

- once fit is confirmed, move into a structured pilot proposal rather than abstract discussion

Supporting assets:

- `PILOT_OFFER_ONE_PAGER.md`
- `PILOT_COMMERCIAL_PROPOSAL_TEMPLATE.md`
- `PILOT_STATEMENT_OF_WORK_TEMPLATE.md`
- `PILOT_SCOPE_AND_PRICING.md`

What to learn:

- whether the prospect is ready to evaluate a fixed-scope pilot
- whether the prospect accepts the narrow wedge and explicit exclusions

## Stop Conditions

Do not push forward if:

- the prospect really wants refunds, batch payments, or broad treasury workflows first
- the prospect wants finished production execution rather than a controlled pilot
- the prospect cannot provide a finance owner and technical owner
- the prospect cannot accept the current simulation boundaries

## Practical Sequence Summary

Use the flow in this order:

1. buyer pain
2. wedge
3. value hypothesis
4. actual pilot workflow
5. limitations and boundaries
6. qualification
7. proposal

That sequence is the most commercially honest fit for the current repo state.
