# Actenon Cloud In Plain English

Actenon Cloud is the private service that decides whether a sensitive finance action should move forward, what approvals and evidence are required, what proof can be issued, and how the final outcome is recorded.

It sits above a separate open execution kernel.

- The open kernel defines the public Action Intent and receipt contracts, execution-side semantics, and verifier logic.
- Actenon Cloud does not replace that kernel.
- Actenon Cloud adds tenant management, policy, approvals, evidence, proof issuance, escrow, receipts, audit, and admin controls around kernel-aligned actions.

## What It Does Today

Today the service can:

- accept an external Action Intent object using a pinned kernel contract
- look up the tenant workflow policy and make a deterministic decision
- create approval requests and track approval decisions
- register or upload evidence and bind it to the Action Intent
- issue a bounded proof when the policy, approval, and evidence conditions are satisfied
- create a tightly scoped capability escrow record tied to that proof
- ingest kernel-aligned receipts and make them searchable
- expose an end-to-end audit trace for a finance action
- enforce basic multi-tenant access control for operators and service principals

## What It Is Good For Right Now

- internal company development
- architecture review
- design-partner walkthroughs
- early pilot integration work with controlled assumptions

## What It Is Not Ready For Yet

It is not yet honest to call this production-ready.

The biggest missing pieces are:

- enterprise SSO and production-grade service identity
- managed KMS or HSM-backed signing
- real external capability release and provider integrations
- stronger production tenant-isolation controls
- production deployment, observability, and operations hardening

## Simple Request Story

1. A tenant submits an Action Intent.
2. The control plane validates the request against the pinned kernel contract.
3. The tenant workflow policy decides whether the action is allowed, denied, or needs more controls.
4. If needed, approvals and evidence are collected.
5. If all conditions are satisfied, the control plane issues a bounded proof.
6. That proof can be used to create and release a tightly scoped capability escrow record.
7. When the downstream system produces a receipt, the control plane stores it and links it back to the original action, proof, approvals, evidence, and audit trail.

## The Important Boundary

The open kernel is the shared, public execution substrate.

Actenon Cloud is the private, commercial governance layer above it.

That boundary is deliberate and should stay intact.
