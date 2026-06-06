# Sales Readiness Checklist

## Purpose

This checklist helps a founder, operator, or early commercial lead prepare for serious design-partner conversations about the invoice payment execution pilot.

It is designed to keep technical truth, pilot readiness, and pricing logic aligned.

## Core Readiness Standard

Before running outreach or a serious meeting, be able to explain all of the following clearly:

- what the pilot is
- why invoice payment execution is the first wedge
- what is real today
- what is still early or simulated
- how the pilot is packaged
- why the pricing logic is fair
- why blocked actions are not charged

## Pre-Meeting Checklist

Before the meeting, confirm:

- the prospect has a real outbound invoice payment workflow
- the prospect is open to a narrow pilot rather than a broad platform evaluation
- the internal lead can explain the control-plane versus verifier boundary cleanly
- the internal lead can explain pilot readiness as `Amber`, not `Green`
- the internal lead can explain that the pilot is fixed-fee and fixed-scope
- the internal lead can explain that the live model is hybrid: fixed setup work plus usage on proved and allowed actions
- the internal lead can explain why blocked actions are not charged as usage

## Documents To Have Open During The Meeting

- [BUYER_PROBLEM.md](BUYER_PROBLEM.md)
- [WEDGE_NARRATIVE.md](WEDGE_NARRATIVE.md)
- [DESIGN_PARTNER_ONE_PAGER.md](DESIGN_PARTNER_ONE_PAGER.md)
- [DESIGN_PARTNER_FAQ.md](DESIGN_PARTNER_FAQ.md)
- [OBJECTION_HANDLING.md](OBJECTION_HANDLING.md)
- [PILOT_PACKAGING.md](PILOT_PACKAGING.md)
- [PILOT_PRICING_ASSUMPTIONS.md](PILOT_PRICING_ASSUMPTIONS.md)
- [COMMERCIAL_MODEL_DRAFT.md](COMMERCIAL_MODEL_DRAFT.md)
- [CONTROL_PLANE_RELEASE_READINESS.md](CONTROL_PLANE_RELEASE_READINESS.md)
- [BLOCKERS.md](BLOCKERS.md)

## Meeting Narrative Checklist

In the meeting, make sure the conversation covers:

### 1. Buyer Problem First

- invoice payment review is often fragmented
- approvals, evidence, release, and receipts are hard to trace together
- the buyer pain is control ambiguity, not just workflow inconvenience

### 2. Wedge Second

- the first wedge is one outbound invoice payment workflow
- not refunds
- not batch payments
- not broad finance automation

### 3. Pilot Truth Third

- the pilot is real and narrow
- it governs the decision path before execution
- it does not claim finished production execution
- proof verification remains external through a separate verifier repo or verifier interface

### 4. Pricing Logic Fourth

- the pilot is a fixed-fee, fixed-scope engagement because value includes setup, mapping, validation, and supervised delivery
- later live use is best explained as usage pricing tied to proved and allowed actions, with setup or rollout work scoped separately when needed
- blocked actions are not charged as usage

## Pricing Readiness Checklist

Before discussing money, be able to explain:

- why the pilot is not metered per action
- why later live use should not default to a generic seat model
- why setup work and live action usage should be priced separately
- why pricing on proved and allowed actions is stronger than generic subscription language
- why blocked actions are free from a usage-pricing standpoint

## Strong Pricing Language

Use language like:

- "The pilot is a fixed-fee, fixed-scope evaluation because most of the early value comes from workflow setup, control mapping, validation, and supervised delivery."
- "After setup work, the cleanest live usage meter is the proved and allowed consequential action."
- "We do not charge usage for blocked actions because that would create distrust and misaligned incentives."

## Language To Avoid

Avoid saying:

- "This is just a SaaS subscription"
- "You pay for every action attempt"
- "We charge for blocked actions too"
- "This repo is the verifier"
- "This is ready for production deployment"
- "This replaces your payment systems"

## Qualification Checklist

The meeting should confirm:

- there is a finance sponsor
- there is a technical owner
- there is one invoice payment workflow worth testing
- the prospect accepts a controlled pilot
- the prospect accepts explicit simulation boundaries
- the prospect can support pilot setup and receipt integration inputs

## Stop Conditions

Do not advance the commercial process if:

- the buyer wants a broad treasury platform now
- the buyer wants refunds or batches first
- the buyer cannot accept current pilot limits
- the buyer wants finished production execution immediately
- the team cannot explain pricing without falling back to generic subscription language

## Remaining Internal Cleanup Notes

The current materials are mostly coherent, but these internal cautions still matter:

- `README.md` is still repo-oriented rather than conversation-oriented
- some technical documents naturally use system-native terms before buyer terms
- the current hybrid model still needs disciplined explanation so setup work is not confused with generic software-access pricing

## Best Checklist Summary

If the team can explain:

- the buyer problem
- the narrow wedge
- the real pilot
- the fixed-fee pilot model
- the later proved-and-allowed-action usage model
- and why blocked actions are not charged

then the team is commercially ready for serious early design-partner meetings.
