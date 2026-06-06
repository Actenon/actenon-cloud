# Pilot Commercial Proposal Template

## Purpose

This template is for a commercial proposal for the invoice payment execution governance pilot.

This is a proposal template, not a claim that final pricing or contract terms have already been approved.

## 1. Proposal Summary

- Customer: `[customer name]`
- Pilot name: `Invoice Payment Execution Governance Pilot`
- Proposal date: `[date]`
- Proposed start window: `[date range]`
- Proposed duration: `6 to 8 weeks`
- Proposal owner: `[owner]`
- Commercial model: `fixed-fee, fixed-scope pilot`

## 2. Customer Problem Statement

`[Describe the current invoice payment control problem in plain language.]`

Suggested areas:

- manual approval ambiguity
- fragmented evidence collection
- weak traceability from payment proposal to receipt
- difficulty explaining why a payment was allowed or blocked

## 3. Pilot Objective

The objective of this pilot is to evaluate whether Actenon Cloud can provide a commercially meaningful control layer for outbound invoice payment execution by:

- governing invoice payment proposals before execution
- requiring approvals and evidence where appropriate
- issuing bounded proofs for exact payments
- improving receipt and audit traceability

## 4. Pilot Scope

In scope:

- one pilot tenant
- outbound invoice payment execution governance
- one invoice payment workflow family only
- policy setup for the chosen payment workflow
- approval and evidence workflows
- proof issuance and escrow lifecycle
- receipt ingestion and audit trace review

Out of scope:

- refunds
- generalized payment automation
- production identity rollout
- managed signing rollout
- production deployment hardening

## 5. Customer Responsibilities

The customer is responsible for providing:

- pilot sponsor
- technical owner
- finance operations owner
- named requesters, approvers, and release managers
- invoice payment proposal inputs
- policy and approval thresholds
- evidence expectations
- receipt source and posting path
- pilot environment inputs and security approvals

Typical customer systems involved:

- ERP or payable system
- payment operations workflow or connector-adjacent process
- receipt-producing downstream execution path

## 6. Deliverables

Actenon Cloud will provide:

- pilot-scope workflow configuration
- policy setup for the chosen invoice payment controls
- seeded validation scenarios
- operator workflow guidance
- support during pilot execution
- final pilot findings review
- recommended next-step hardening path if the pilot succeeds

## 7. Success Measures

Suggested success measures:

- blocked invalid or unsafe payment proposals
- clear approval and evidence visibility
- traceable receipt linkage
- operator confidence improvement
- explicit post-pilot hardening recommendation

## 8. Commercial Structure

Recommended structure for the current stage:

- a paid, fixed-scope pilot
- one suggested time box of `6 to 8 weeks`
- one defined support model
- optional separately scoped integration services if customer-specific adapter work is requested
- one fixed-fee commercial structure without claiming public list pricing

Commercial fields to complete:

- pilot fee: `[to be approved]`
- optional integration services fee: `[to be approved]`
- optional extension fee: `[to be approved]`
- billing schedule: `[to be approved]`

See `PILOT_SCOPE_AND_PRICING.md` for the packaging logic behind these terms.

## 9. Risks And Limitations

The pilot is intentionally narrow and not production-ready.

Key limitations:

- capability release is simulated
- auth is early
- signing is early
- observability is limited

## 10. Decision Path After Pilot

If the pilot succeeds, the next proposed commercial step is a production-hardening plan that addresses:

- enterprise identity
- managed signing
- real capability release
- production deployment controls
- stronger tenant isolation
- possible expansion from one invoice payment workflow to a broader paid control-plane deployment
