# Pilot Pricing Assumptions

## Purpose

This document states the pricing assumptions behind the current pilot packaging and commercial model draft.

These are working assumptions, not final approved pricing policy.

## Core Assumption

The pilot should be priced around delivery effort and controlled workflow validation, not around raw transaction volume.

That is because current pilot value depends on:

- implementation support
- workflow mapping
- policy setup
- approval and evidence configuration
- receipt and audit review
- supervised validation

## Why Pure Subscription Is Not Strong Enough For The Pilot

A pure recurring subscription or generic platform-access fee is too abstract as the only commercial logic for this stage.

It can work later for ongoing platform access, but for the current pilot it hides the fact that the customer is paying for:

- structured pilot delivery
- a narrow workflow outcome
- shared implementation and readiness work

## Why Pure Per-Action Pricing Is Not Strong Enough For The Pilot

A pure per-action price is also weak for the current pilot stage because:

- pilot volumes may be intentionally low
- a large share of the work happens before volume exists
- the customer is evaluating control quality, not only throughput
- a per-action model during the pilot would make value harder to predict

For pilot conversations, predictability and fairness matter more than metering.

## Assumption For Live Operational Use

If the partner moves past the pilot, the strongest model to use is:

- setup or rollout work charged separately when required
- plus usage-based pricing for proved and allowed actions

The usage component reflects value from:

- real consequential actions that were governed and allowed to progress
- action-linked control outcomes that are easy for buyers to understand

This keeps the commercial model closer to the consequential value created by the product and avoids falling back to generic software-access pricing language.

## Treatment Of Proved And Allowed Actions

The pricing unit that is most commercially legible for later operational use is:

- a proved and allowed consequential action

For this wedge, that means an invoice payment request that:

- passed through governance
- satisfied required controls
- received proof issuance
- was allowed to move forward as a governed action

This is a cleaner unit than charging for every intake request.

## Treatment Of Blocked, Denied, Or Prevented Actions

The default recommended pricing treatment is:

- blocked, denied, prevented, or structurally non-executable actions should not be charged as usage

This is recommended for three reasons:

### 1. Trust

Charging for blocked actions can create immediate buyer suspicion that the vendor benefits from friction.

### 2. Incentive Alignment

The product should be seen as aligned with safe decision-making, not as monetizing rejection volume.

### 3. Simplicity

The commercial story is much easier to explain if customers pay for:

- the pilot itself
- real governed actions that progressed

and not for every rejected or blocked event.

## Important Exception

This does not mean blocked actions have no value.

They absolutely can demonstrate product value in the pilot. But that value should support:

- pilot justification
- later renewal logic
- proof of control effectiveness

not line-item usage charges.

## Treatment Of Setup And Implementation Work

Setup and implementation work should be charged separately from live operational use.

For the current pilot stage, that means:

- fixed pilot or setup fee for the base engagement
- separately scoped fees for optional integration or extension work

That fixed pilot or setup fee covers:

- workflow mapping
- configuration and control setup
- validation scenarios
- supervised delivery and review

It should not mean:

- burying all setup effort in a later per-action price
- pretending the pilot is already steady-state SaaS

## External Verifier Dependency Assumption

This repo depends on a separate verifier repo or verifier interface for proof verification when verification is needed.

Current pricing assumptions do not assign standalone pricing or licensing treatment to that external verifier dependency inside this repo's pilot package.

If deeper verifier integration or compatibility hardening becomes part of a customer-specific engagement, that should be scoped separately rather than implied as bundled pricing logic here.

## Commercial Assumption Summary

The working pricing assumptions are:

- charge a fixed pilot or setup fee for the pilot
- scope extra implementation work separately
- do not meter the pilot per action
- if the pilot succeeds, use usage pricing tied to proved and allowed actions
- do not charge usage for blocked or denied actions

That is the cleanest fit for early design-partner conversations.
