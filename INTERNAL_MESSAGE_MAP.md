# Internal Message Map

## Purpose

This document gives the internal message map for design-partner conversations.

It aligns:

- technical truth
- pilot readiness
- commercial language
- pricing logic

## One-Sentence Company-Level Message

Actenon Cloud is a commercial governance and traceability layer for outbound invoice payment execution, offered first through a controlled design-partner pilot.

## Core Problem Message

Invoice payment decisions are often hard to review, hard to explain, and hard to trace from proposal to receipt because approvals, evidence, release decisions, and receipts are fragmented across systems.

## Core Wedge Message

The first wedge is one outbound invoice payment workflow because it is narrow, commercially legible, measurable, and already supported by the implemented control-plane workflow.

## Core Pilot Message

The pilot tests whether a dedicated control plane can make one invoice payment workflow safer, clearer, and easier to trace before broader production-hardening work is justified.

## Core Boundary Message

This repo is the control plane. The open kernel remains separate, and proof verification remains external through a separate verifier repo or verifier interface.

## Core Pricing Message

The pilot should be sold as:

- fixed fee
- fixed scope
- fixed time box

because current value comes from both product capability and delivery effort.

If the pilot succeeds, the strongest later commercial direction to test is:

- setup or rollout work charged separately when needed
- plus per proved and allowed consequential action

## Why This Pricing Model Is Stronger Than Generic SaaS Messaging

### Why It Is Stronger Than A Pure Subscription Story

A pure subscription story is too weak for this product today because:

- the pilot includes real setup and validation work
- the wedge creates value around consequential governed actions, not just abstract access
- buyers will want pricing to reflect the seriousness of invoice payment outcomes

### Why It Is Stronger Than A Pure Seat Model

A seat model is weaker because:

- value is not mainly created by the number of users
- the wedge is about governed payment outcomes and traceability
- a seat model feels generic and disconnected from the actual workflow value

### Why It Is Stronger Than Pure Per-Action Pricing In The Pilot

Pure per-action pricing is weaker during the pilot because:

- volume is low and intentionally controlled
- the work is front-loaded
- predictability matters more than metering in an early pilot

## Message On Blocked Actions

Blocked actions are valuable, but they should not be charged as usage.

Internal reason:

- charging for blocked actions creates distrust
- it can make incentives look misaligned
- it is easier to explain that customers pay for the pilot and later for consequential governed actions that were actually allowed to progress

External short version:

- "We do not charge usage for blocked actions because the commercial model should reward aligned governed outcomes, not friction."

## Buyer-Specific Message Variants

### Finance Sponsor

Lead with:

- unsafe payments can be stopped earlier
- approvals and evidence become easier to review
- receipts are easier to connect back to the original decision

Avoid leading with:

- verifier architecture
- low-level contract semantics

### Technical Owner

Lead with:

- the pilot is narrow and bounded
- the control-plane versus verifier boundary is explicit
- the pilot does not require pretending production readiness

Avoid leading with:

- broad future packaging
- speculative integration promises

### Internal Commercial Lead

Lead with:

- fixed-fee pilot now
- hybrid later if the pilot succeeds
- no usage charge for blocked actions

Avoid:

- defaulting to "software subscription" language
- collapsing everything into generic SaaS language because it feels familiar

## Ready Answers To Common Internal Questions

### "Why are we not just selling a subscription?"

Because the pilot is still a controlled engagement with meaningful implementation and validation work, and because the product's long-term value is linked partly to consequential allowed actions rather than generic access alone.

### "Why are we not charging for blocked actions if blocking is valuable?"

Because prevention value should strengthen the platform case, not look like metered rejection revenue. Charging for blocked actions can undermine trust right when trust matters most.

### "Why not make live pricing purely action-based?"

Because some work is still not action-meter work:

- setup
- rollout
- integration changes
- readiness work

Those are better scoped explicitly, while live governed actions are priced on the proved and allowed action meter.

## Internal Warnings

These message drifts should be corrected immediately:

- describing the repo as the verifier
- describing the pilot as production-ready
- describing the offering as a generic SaaS platform
- describing pricing as final policy
- implying that blocked actions are monetized

## Remaining Commercially Weak Or Confusing Language

The main remaining weak spots are:

- `README.md` remains a repo document, not a commercial intro
- some internal docs still use system-native terms before buyer-friendly terms
- some pricing docs still need careful reading so people do not slide back into generic platform-fee language by habit

## Best Internal Summary

The cleanest internal story is:

- one painful invoice payment workflow
- one controlled pilot
- one fixed pilot fee for setup, implementation, validation, and delivery
- one live usage meter: the proved and allowed consequential action
- separate scoped charges for rollout or extra integration work when needed
- zero usage charge for blocked actions

That is the strongest commercially coherent message supported by the current repo.
