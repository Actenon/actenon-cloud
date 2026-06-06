# Buyer Problem

## Purpose

This document states the buyer problem for the current Actenon Cloud pilot in plain commercial language.

It is intentionally narrow. It is about outbound invoice payment execution, not generalized finance automation.

## The Core Buyer Problem

Many finance teams still move invoice payments through a process that is fragmented, manual, and hard to explain after the fact.

A typical payment may involve:

- an ERP or payables system
- manual review of invoice details
- email or chat approvals
- separate evidence scattered across inboxes, folders, or ticketing tools
- a downstream payment operation
- a receipt or result that is hard to connect back to the original decision

The result is not just inconvenience. The result is control ambiguity.

## What Hurts In Practice

The buyer pain is usually some combination of:

- uncertainty about whether the right payee, amount, and account details were checked before release
- inconsistent approval handling for higher-risk payments
- evidence that exists, but is hard to find when a payment is reviewed later
- difficulty explaining why a payment was allowed, delayed, or blocked
- fragmented audit trails across multiple tools and teams
- manual handoffs that make exceptions harder to understand

## Why This Matters To A Finance Buyer

For a finance leader or finance operations owner, the pain is not only technical.

The operational problem is that outbound invoice payments can become:

- harder to review consistently
- harder to defend during audit or internal review
- harder to investigate when something looks wrong
- harder to improve because the decision path is not visible in one place

Even when a payment is ultimately correct, the process around it may still be weak, slow, or ambiguous.

## The Narrow Problem This Pilot Tries To Solve

The pilot does not try to solve every finance workflow.

It tries to solve one narrower question:

Can a dedicated control plane make outbound invoice payment decisions safer, clearer, and easier to audit before broader production hardening is funded?

In practical terms, that means:

- proposals are evaluated before execution
- policy decisions are explicit
- approvals and evidence are attached to the payment record
- release state is visible
- the resulting receipt can be linked back to the original governed decision

## What Makes This Problem Worth Starting With

Invoice payment execution is a good first problem because it is:

- operationally familiar to finance teams
- narrow enough to pilot safely
- important enough to justify attention
- measurable without needing a broad transformation program

## What This Problem Statement Does Not Claim

This buyer problem statement does not claim:

- that Actenon Cloud already provides finished production payment execution
- that this repo performs proof verification itself
- that all downstream payment infrastructure can be replaced by this pilot
- that the pilot solves every payment or treasury workflow

Proof verification remains available through a separate verifier repo or verifier interface outside this repository. That matters for system truth, but it is not the primary buyer story.

## Buyer-Level Summary

The buyer problem is simple:

Too many invoice payment decisions are difficult to review, difficult to explain, and difficult to trace across the full path from proposal to receipt.

The pilot exists to test whether Actenon Cloud can make that path more controlled and more understandable for one narrow invoice payment workflow.
