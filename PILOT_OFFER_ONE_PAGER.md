# Pilot Offer One Pager

## Offer Name

Invoice Payment Execution Governance Pilot

## What This Pilot Is

This pilot packages Actenon Cloud as the governance and traceability layer for outbound invoice payment execution.

The pilot helps a design partner answer one focused question:

Can a dedicated control plane reduce ambiguity and operational risk around invoice payment decisions before broader production hardening is justified?

Suggested pilot shape:

- one invoice payment execution workflow
- one tenant
- one fixed-fee, fixed-scope pilot
- suggested duration: `6 to 8 weeks`

## Who This Is For

Best-fit design partners are organizations that already have:

- a real outbound invoice payment process
- a finance operations or accounts payable team
- an existing payment execution path outside this repo
- a desire to improve approval clarity, evidence handling, and end-to-end payment traceability

Primary pilot stakeholders usually include:

- a finance operations leader
- an accounts payable process owner
- a technical owner
- a pilot sponsor
- named approvers and release operators

Typical customer systems involved:

- payable or ERP system that originates the payment proposal
- payment operations process that performs the actual payment step
- receipt source that can post execution outcomes back into the control plane

## What Problem It Solves

Many invoice payment processes still rely on fragmented controls spread across:

- ERP exports
- email approvals
- manual evidence collection
- payment-provider actions
- disconnected audit trails

This pilot narrows that problem to one workflow:

- govern a proposed invoice payment before execution
- require approvals and evidence when needed
- issue a bounded proof for the exact payment
- track release, receipt, and audit traceability end to end

## What Is In Scope

- one tenant pilot
- one workflow family: outbound invoice payments
- one kernel action profile: `action_type="payment"`
- policy evaluation
- approval workflow
- evidence registration or upload
- proof issuance
- capability escrow lifecycle
- receipt ingestion and searchable audit trace

## What Is Out Of Scope

- refunds
- batch payments
- payouts
- collections
- production-grade provider execution automation
- enterprise SSO rollout
- managed KMS or HSM signing rollout
- production deployment hardening

## What The Customer Must Provide

- pilot sponsor, technical owner, and finance operations owner
- requester, approver, and release-manager users
- invoice payment proposal source
- policy thresholds and blocked-destination rules
- approval and evidence rules
- receipt source from the customer payment process
- pilot environment inputs such as managed database, storage, TLS, and non-default secrets

## What Actenon Cloud Provides

- tenant and workflow setup guidance
- pilot-scope policy configuration
- control-plane workflow enablement for intake, approval, evidence, proof, escrow, and receipts
- seeded validation scenarios
- trace review and pilot-readout support
- a final pilot review with a recommended next-step hardening path

## What Success Looks Like

- invalid or unsafe invoice payments are blocked before execution
- high-risk payments clearly require approval and or evidence
- approved payments have a coherent trace from proposal through receipt
- operators can explain why a payment was allowed, denied, delayed, revoked, or quarantined
- the design partner can name the exact hardening work needed for production

## Current Limitations

- capability release is still simulated in this repo
- auth and service identity are still early
- signing is still early unless upgraded outside the current pilot scope
- the pilot does not claim production-readiness
- the pilot does not claim that this repo executes invoice payments directly

## What The Pilot Does Not Claim

- production-ready payment execution
- enterprise-ready identity
- managed signing maturity
- real protected-resource broker enforcement
- finished production operations posture

## Commercial Next Step After Success

If the pilot succeeds, the next step is not “go live immediately.”

The next step is a production-hardening decision covering:

- identity
- signing
- real capability release
- deployment and observability
- stronger tenant-isolation controls
- potential expansion from one invoice payment workflow to a broader paid control-plane rollout
