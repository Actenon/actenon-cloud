# Integration Assumptions

## Purpose

This document captures the working integration assumptions for Actenon Cloud.

It is intentionally narrow and aligned to the invoice payment execution pilot.

## Assumption 1: Kernel Contracts Stay External

Actenon Cloud accepts and stores finance Action Intents and receipts that align to contracts published by the separate open kernel repo.

This repo may pin local copies for development and testing, but those contracts are not owned here.

## Assumption 2: Proof Verification Stays External

Actenon Cloud may issue bounded proofs as part of the governed payment flow.

Proof verification is not performed by this repository. When proof verification is needed, it must come from a separate verifier repo or verifier interface outside this codebase.

## Assumption 3: Execution Still Happens Outside This Repo

Actenon Cloud governs execution readiness and records release state, but actual invoice payment execution still happens in customer systems, adjacent adapters, or future external execution components.

## Assumption 4: Receipt Truth Comes Back From Outside

Receipt ingestion assumes that an external execution path produces a kernel-aligned receipt and posts it back to Actenon Cloud for indexing, reconciliation, and audit.

## Assumption 5: Pilot Release Is Still Simulated

For the current pilot posture, capability release remains simulated in this repo unless a separate shallow integration is added.

That simulation boundary does not change the repo boundary around verifier logic.

## Assumption 6: Buyer Messaging Must Reflect The Real Split

Commercial and pilot-facing materials should describe the flow as:

1. Actenon Cloud governs the invoice payment decision.
2. Actenon Cloud issues a bounded proof.
3. A separate verifier interface can validate that proof if the workflow requires verification.
4. An external execution path performs the payment.
5. A receipt comes back into Actenon Cloud for traceability.

## Assumption 7: No Verifier Logic Should Drift Inward

If new work would require implementing proof validation semantics inside this repo, that work is out of bounds for Actenon Cloud and should stay with the separate verifier repo or interface.
