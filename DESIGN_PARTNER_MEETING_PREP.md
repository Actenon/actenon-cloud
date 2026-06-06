# Design Partner Meeting Prep

## Purpose

This document is a practical prep guide for first and second design-partner meetings about the invoice payment execution pilot.

It is intended to make meetings easier to run without drifting into unsupported claims.

## Primary Objective

The objective of the first serious meeting is not to close a production deployment.

The objective is to determine whether the prospect has:

- a real invoice payment control problem
- a workable pilot scope
- the right team and expectations for a controlled pilot

## Secondary Objective

If the fit is real, the secondary objective is to leave the meeting with agreement on:

- why the invoice payment wedge matters
- what the pilot would and would not cover
- why the pilot is priced as a fixed-fee engagement
- what the buyer would pay for during live use
- why blocked actions are not charged as usage

## Recommended Meeting Sequence

### 1. Open With The Problem

Lead with:

- invoice payment decisions are often hard to review, hard to explain, and hard to trace from proposal to receipt

Do not open with:

- repo layout
- verifier architecture
- abstract control-plane language

## 2. Narrow To The Wedge

Say clearly:

- this is one outbound invoice payment workflow
- it is not a broad finance automation pitch
- it is not a production rollout pitch

## 3. Explain What The Pilot Actually Does

Use a short version of the flow:

- payment proposal enters the governed path
- policy decides whether the action is allowed, denied, or requires more controls
- approvals and evidence are attached when required
- a bounded proof is issued for the exact payment
- release state is recorded
- the resulting receipt is linked back into one trace

If asked about verification:

- say proof verification is external through a separate verifier repo or verifier interface
- do not let the meeting turn into a verifier deep dive unless the technical buyer needs that clarification

## 4. State The Current Limits Early

Say clearly:

- pilot readiness is amber
- capability release is still simulated
- auth is still early
- signing is still early
- this is not a production-readiness claim

## 5. Explain Pricing In The Right Order

Use this order:

### Pilot Pricing Now

- fixed pilot fee
- fixed scope
- fixed time box
- optional separately scoped integration work

Why:

- the pilot includes implementation, workflow mapping, validation, and delivery work

### Live Pricing Later

- after the pilot, the live model is best explained as usage tied to proved and allowed consequential actions
- setup, rollout, and extra integration work remain separately scoped when needed

Why:

- the most legible usage unit is the consequential action that was actually governed and allowed to progress
- setup work should be priced separately instead of being hidden inside a generic software fee

### Blocked Actions

- blocked actions are not charged as usage

Why:

- charging for blocked actions can create distrust
- it can look like the vendor profits from friction
- prevention value should support the case for the platform, not be a separate line-item meter

## Recommended Questions To Ask

### Problem Questions

- Where does invoice payment review break down today?
- What makes a payment hard to explain later?
- Where are approvals and evidence tracked today?

### Scope Questions

- Can you identify one invoice payment workflow to isolate for a pilot?
- Are refunds, batches, or broader workflows likely to creep into scope?

### Readiness Questions

- Who would sponsor the pilot on the finance side?
- Who would own setup on the technical side?
- Can your team work within a controlled pilot with explicit simulation boundaries?

### Commercial Questions

- Would a fixed-fee pilot be easier to approve than an experimental usage-based pilot price?
- If the pilot worked, would usage pricing on proved and allowed actions feel fairer than a generic software subscription?

## Documents To Use In The Meeting

- [DESIGN_PARTNER_ONE_PAGER.md](DESIGN_PARTNER_ONE_PAGER.md)
- [DESIGN_PARTNER_FAQ.md](DESIGN_PARTNER_FAQ.md)
- [OBJECTION_HANDLING.md](OBJECTION_HANDLING.md)
- [PILOT_PACKAGING.md](PILOT_PACKAGING.md)
- [PILOT_PRICING_ASSUMPTIONS.md](PILOT_PRICING_ASSUMPTIONS.md)
- [COMMERCIAL_MODEL_DRAFT.md](COMMERCIAL_MODEL_DRAFT.md)

## Signals The Meeting Is Going Well

- the buyer agrees the pain is real
- the buyer accepts the narrow wedge
- the buyer understands that the pilot is controlled, not production-ready
- the buyer sees why the pilot is fixed-fee
- the buyer reacts positively to not charging for blocked actions
- the buyer sees logic in setup-fee-now plus proved-and-allowed-action pricing later

## Signals To Slow Down Or Stop

- the buyer keeps pulling the conversation toward broad workflow expansion
- the buyer wants pricing for generalized platform access immediately
- the buyer expects production execution or production auth in the pilot
- the buyer distrusts the no-charge treatment for blocked actions because the rationale is unclear
- the internal team cannot explain why pure subscription is weaker for this wedge

## Best Meeting Close

The ideal close is:

- agreement that the buyer problem is real
- agreement that invoice payment execution is the right first wedge
- agreement that a fixed-fee pilot is the right current commercial structure
- agreement that later operational pricing, if the pilot succeeds, should be tied to proved and allowed actions rather than generic software access

That is the cleanest path into a serious design-partner motion.
