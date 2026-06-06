# Design Partner Pilot Overview

## Pilot Decision

The recommended design-partner pilot wedge for Actenon Cloud is outbound invoice payment execution.

This is the strongest current wedge because:

- the pinned finance Action Intent contract already supports `action_type="payment"`
- the current control-plane implementation already supports intake, policy, approvals, evidence, proof issuance, escrow lifecycle, receipt ingestion, reconciliation, and audit traceability for finance actions
- refund execution is not a first-class action type in the current pinned kernel finance contract, so packaging refunds first would be less honest and less commercially strong

## Problem This Pilot Solves

Many invoice-payment workflows still depend on a mix of ERP exports, email approvals, manual evidence checks, and payment-provider execution steps that are difficult to audit end to end.

This pilot packages Actenon Cloud as the governed decision layer in front of invoice payment execution. The goal is to make one narrow workflow safer and easier to understand:

- propose an invoice payment
- evaluate tenant policy deterministically
- gather required approvals and evidence
- mint a bounded proof for the exact payment
- rely on a separate verifier repo or verifier interface for proof verification where needed
- release or refuse execution authority
- ingest the resulting receipt and expose a searchable audit trace

## Exact Pilot Workflow

The pilot focuses on one outbound invoice payment at a time.

Recommended pilot request profile:

- `kernel_action_intent.action_type = "payment"`
- `kernel_action_intent.workflow_key = "payments.standard"`
- one positive `amount_minor`
- one `currency`
- one `source_account_ref`
- one `destination_account_ref`
- invoice identifiers carried in `external_reference` and or `kernel_action_intent.metadata`

## What The Design Partner Sees

The design partner gets a narrow, concrete finance-control workflow:

1. submit invoice payment proposals into Actenon Cloud
2. apply explicit policy and hard rules before execution
3. collect approvals and evidence for higher-risk payments
4. issue a bounded proof tied to the exact payment payload
5. release a tightly scoped capability for downstream execution
6. ingest receipts and review the complete trace

## What Is Commercially Valuable In The Pilot

- invalid invoice payments can be blocked before execution
- approval ambiguity becomes visible and queryable
- evidence is attached to the governed payment rather than scattered across tools
- the resulting payment trace can be reviewed by operators, finance leads, and auditors
- the partner can evaluate whether this control-plane layer is worth hardening into a production execution path

## What Is Still Simulated

The pilot must remain explicit about current limits:

- capability release is still simulated in this repo unless a separate shallow adapter is added later
- operator auth is still early and does not equal enterprise SSO
- signing is still development-local unless separately upgraded
- observability is still scaffolded, not fully operationalized

## Pilot Outcome

A successful pilot does not prove full production readiness. It proves that a serious finance design partner can use Actenon Cloud to govern invoice payment decisions, produce bounded proofs, and maintain a coherent receipt and audit trace around real payment operations.

Proof verification remains outside this repo and depends on a separate verifier interface.
