# Design Partner One Pager

## What Actenon Cloud Is

Actenon Cloud is the private commercial control layer for governed invoice payment execution.

The current design-partner pilot is intentionally narrow. It is focused on one outbound invoice payment workflow, not broad finance automation and not a production-readiness claim.

## The Problem

Many invoice payments still move through a fragmented process:

- payment details are proposed in one system
- approvals happen in email, chat, or separate tools
- evidence is scattered across folders or inboxes
- release decisions are hard to explain later
- receipts are hard to connect back to the original decision

The real pain is control ambiguity. Teams struggle to answer simple questions after the fact:

- why was this payment allowed
- who approved it
- what evidence existed
- what happened after release

## The Pilot Wedge

The first pilot wedge is outbound invoice payment execution governance.

That wedge is the right place to start because it is:

- narrow enough to pilot safely
- important enough to matter to finance leaders
- measurable through blocked unsafe payments, approval visibility, and receipt traceability
- already supported by the current implementation

## What The Pilot Does

For one invoice payment workflow, Actenon Cloud can:

- accept a payment proposal
- evaluate policy before execution
- require approvals or evidence when needed
- issue a bounded proof for the exact governed payment
- track release state
- ingest the resulting receipt
- expose one searchable audit trace from proposal to receipt

Proof verification remains separate and external to this repository through a separate verifier repo or verifier interface when that workflow requires verification.

## What The Design Partner Gets

The design partner gets a controlled way to test whether a dedicated control plane improves invoice payment review and traceability.

The immediate value is not “full automation.” The immediate value is:

- clearer payment decisions
- earlier blocking of unsafe payments
- visible approval and evidence handling
- stronger traceability from request to receipt

## How The Pilot Is Packaged

The pilot is sold first as a fixed pilot or setup engagement, not as generic software access.

That fixed fee covers:

- workflow mapping
- tenant and policy configuration
- validation scenarios
- supervised pilot delivery

If the pilot proves valuable enough to continue, the working live commercial direction is usage pricing tied to proved and allowed invoice payment actions. Blocked or denied actions are not billed as usage.

## What Is In Scope

- one tenant
- one outbound invoice payment workflow family
- one governed payment request at a time
- controlled pilot operation
- explicit success criteria and pilot review

## What Is Out Of Scope

- refunds
- batch payments
- broad treasury workflows
- production-grade connector or broker operations
- enterprise-ready identity rollout
- production-ready managed signing
- finished production payment execution

## Current Pilot Reality

Current pilot readiness is `Amber`.

What is real today:

- policy gating
- approval and evidence workflow
- bounded proof issuance
- release-state tracking
- receipt ingestion
- audit traceability

What is still early or simulated:

- capability release is still simulated
- operator auth is still early
- signing is still development-local unless upgraded separately
- observability is still partial

## What Success Looks Like

A successful pilot shows that a finance team can:

- block unsafe invoice payments before execution
- make approval and evidence requirements explicit
- understand why a payment was allowed or refused
- review a receipt-linked trace without reconstructing the story from multiple tools

## The Commercial Question

The pilot exists to answer one practical question:

Is this invoice payment control layer valuable enough in one real workflow to justify production-hardening work afterward?

That is the right question for the current maturity stage.
