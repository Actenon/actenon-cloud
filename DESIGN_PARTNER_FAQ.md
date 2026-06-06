# Design Partner FAQ

## What is the pilot actually for?

The pilot is for one narrow question:

Can Actenon Cloud make outbound invoice payment decisions safer, clearer, and easier to trace for one real workflow?

## Who is this pilot for?

It is best for organizations that already have:

- a real outbound invoice payment process
- a finance operations or accounts payable owner
- a downstream payment execution path outside this repo
- a desire to improve review clarity, approval discipline, and audit traceability

## What problem does it solve first?

It addresses fragmented payment review.

The target pain is not just slow process. It is a decision path that is hard to explain because proposal details, approvals, evidence, release decisions, and receipts are spread across different systems.

## Why start with invoice payment execution?

Because it is the strongest current wedge:

- it is commercially easy to understand
- it is narrow enough to pilot
- it is important enough to matter
- the repo already supports the control-plane workflow around it

## Does Actenon Cloud execute the payment?

Not in the current pilot.

The pilot governs the decision path before execution, issues proof records, tracks release state, and ingests receipts. The actual payment step still happens in customer systems or adjacent execution components.

## Does this repo perform proof verification?

No.

Proof verification remains external through a separate verifier repo or verifier interface. This repo may issue proofs and track proof-related workflow state, but it does not contain verifier logic.

## What is real today in the pilot?

The pilot already supports:

- payment proposal intake
- deterministic policy decisions
- approval workflow
- evidence handling
- bounded proof issuance
- release-state tracking
- receipt ingestion
- audit trace queries

## What is still simulated or early?

- capability release is still simulated
- operator auth is still early and not enterprise SSO
- signing is still development-local unless upgraded separately
- observability is still limited

## Is this production-ready?

No.

Internal development readiness is green, design-partner pilot readiness is amber, and production deployment readiness is red. The pilot is intentionally a controlled evaluation, not a production deployment claim.

## What would a design partner need to provide?

- a finance sponsor
- a technical owner
- a real invoice payment workflow in scope
- named requesters, approvers, and release operators
- a payment proposal source
- a receipt source from the downstream payment process
- willingness to operate within the current pilot boundaries

## What makes the pilot successful?

Success means the partner can show that the control plane:

- blocks unsafe payments earlier
- makes approvals and evidence easier to understand
- makes the release decision visible
- links the receipt back to the original governed decision

## How is the pilot priced?

The current pilot is meant to be sold as a fixed pilot or setup engagement.

That is because the early value includes workflow mapping, configuration, validation, and supervised delivery, not just software access.

Exact commercial terms remain proposal-based at this stage.

## What would live pricing look like if the pilot succeeds?

The working live commercial direction is usage pricing tied to proved and allowed consequential invoice payment actions.

That keeps pricing closer to the governed business event rather than generic platform access.

## Why are blocked actions not billed?

Blocked, denied, or prevented actions should not be billed as usage in the current model.

They still demonstrate value, but charging for blocked actions can create distrust and make incentives look misaligned. The cleaner story is that the customer pays for the pilot itself and, later, for governed actions that were actually proved, allowed, and progressed.

## What happens if the pilot works?

If the pilot works, the next step is not “go live immediately.”

The next step is to decide whether the workflow is valuable enough to fund production-hardening work such as stronger identity, managed signing, real capability release, better observability, and broader deployment readiness.

## What happens if the pilot does not fit?

That is still a useful outcome.

The pilot should not proceed if the prospect really needs:

- refunds first
- batch payments first
- finished production execution infrastructure
- a broad treasury or finance automation platform

The right first motion is a narrow invoice payment governance pilot, not a broad platform rollout.
