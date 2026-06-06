# Pilot Buyer FAQ

## What is this pilot?

It is a narrow design-partner pilot for outbound invoice payment execution governance.

The pilot helps a customer evaluate whether Actenon Cloud can make invoice payment decisions safer, clearer, and easier to trace before broader production hardening is funded.

## Who is this pilot for?

It is best for organizations that already run an invoice payment process and want stronger governance around:

- policy checks
- approvals
- evidence
- execution authorization
- receipt traceability

It is usually reviewed by both:

- a finance buyer who cares about payment control clarity and auditability
- a technical buyer who cares about integration scope, trust boundaries, and what is still simulated

## Is this a production-ready payment platform?

No.

This pilot is not a production-readiness claim. It is a controlled pilot around governance and traceability for invoice payment execution.

## Does Actenon Cloud execute the payment itself?

Not in the current pilot.

The current repo governs the payment decision and tracks the execution lifecycle, but the actual payment step still comes from the customer process or a future deeper integration.

## What is simulated today?

The biggest simulation boundary is capability release.

The control plane can issue and track the release decision, but the actual protected-resource handoff is still simulated in this repo.

## What does the customer need to provide?

The customer needs to provide:

- pilot stakeholders
- invoice payment proposal source
- policy and approval rules
- receipt source
- pilot environment inputs

Typical users involved:

- payment requester
- approver
- release manager
- finance reviewer
- technical operator

## What will the customer get back?

The customer gets:

- configured pilot workflow
- policy and approval behavior over invoice payments
- receipt and audit trace visibility
- a clear view of what would need to be hardened for production
- a final pilot review and recommended next-step hardening path

## Why not just use an ERP approval flow?

The pilot is not trying to replace every ERP workflow.

It is testing whether a dedicated control plane can create a clearer end-to-end control story across:

- payment proposal
- approval
- evidence
- release decision
- receipt traceability

## What happens if the pilot works?

If the pilot works, the next step is a production-hardening decision, not an immediate production go-live.

Typical next-step topics are:

- enterprise identity
- managed signing
- real capability release
- production deployment hardening
- possible expansion beyond the initial invoice payment workflow

## What happens if the pilot does not work?

The customer should still come away with:

- a clearer view of the real control problem
- evidence on where the current workflow is too weak or too early
- a basis for deciding whether not to continue
