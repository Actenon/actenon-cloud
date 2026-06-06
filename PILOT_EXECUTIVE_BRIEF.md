# Pilot Executive Brief

## Recommended Pilot

The recommended design-partner pilot for Actenon Cloud is invoice payment execution governance.

## Why This Wedge

This is the strongest current commercial wedge because the repo already implements the control layer needed around finance payment actions:

- policy gating
- approval workflow
- evidence handling
- bounded proof issuance
- capability escrow lifecycle
- receipt and audit traceability

Refund execution is not the better first wedge because it is not first-class in the current pinned finance Action Intent contract.

## What The Partner Gets

The design partner gets a narrow but meaningful workflow:

- invoice payment proposals are reviewed before execution
- higher-risk payments can require approvals and evidence
- execution authority is explicitly allowed or refused
- proof verification remains available only through a separate verifier repo or verifier interface
- receipts and audit traces are queryable in one place

## What The Partner Must Accept

This is not a production-readiness claim.

The pilot still has explicit limits:

- capability release is simulated
- auth is early
- signing is early
- observability is early

## Why It Is Still Worth Running

Even with those limits, the pilot can answer a high-value commercial question:

Would a dedicated control plane reduce ambiguity and risk around invoice payment execution enough to justify production hardening?

## Pilot Outcome

If the pilot succeeds, the partner should be able to say:

- invalid invoice payments are easier to block before execution
- approvals and evidence are easier to review
- payment receipts are easier to connect back to the original decision
- the next production-hardening investments are clear
