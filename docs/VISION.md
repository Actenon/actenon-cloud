# Vision

## Purpose

Actenon Cloud exists to provide the governed, enterprise-facing layer above an open execution kernel. It should let organizations intake actions, apply policy, collect approvals, retain evidence, issue customer-facing proofs and receipts, and manage operational controls without re-implementing kernel execution or verification logic.

## Product Thesis

The open kernel should remain the transparent and reusable execution substrate. The hosted control plane should add the capabilities enterprises usually need around that substrate:

- tenancy and isolation
- policy and approval workflows
- evidence custody and auditability
- signing and lifecycle controls
- operational administration and export surfaces

This separation keeps the kernel reusable and inspectable while allowing the control plane to deliver commercial governance features.

## Vision Statement

Build a backend-first control plane that can safely admit Action Intents, govern how they move through approval and evidence workflows, bind them to kernel-aligned receipts and proofs, and expose trustworthy APIs for enterprise operators, auditors, and downstream systems.

## Design Principles

### Separation Of Duties

The control plane governs, stores, signs, routes, and audits. The kernel executes and verifies. When a responsibility is ambiguous, default to keeping execution and verification semantics in the kernel.

### Kernel Alignment Over Forking

The control plane must consume versioned kernel contracts rather than copying logic or inventing local variants. Any contract drift should fail acceptance.

### Evidence-First Operations

Important state transitions should be traceable to evidence, approvals, receipts, or signed artifacts. Operator convenience must not outrank auditability.

### Enterprise Foundations Early

Tenant isolation, authorization, audit logs, exportability, and revocation paths should be designed early because they are hard to retrofit safely.

### Honest Scope

The first release should solve a narrow backend workflow well instead of shipping a thin layer across every future capability.

## Primary Users

- Platform operators who define policy and monitor workflow state
- Security and compliance teams who need evidence, approvals, and exports
- Internal application teams integrating against intake, receipt, and audit APIs
- Administrators managing tenant boundaries, roles, and keys

## Non-Goals For This Pass

- Implementing the production service
- Replacing the open execution kernel
- Finalizing every vendor or infrastructure choice
- Building a broad end-user UI
- Claiming completion of PCCB, signing, or Capability Escrow workflows before interfaces and dependencies are validated

## First Release Outcome

A successful first release gives a tenant-aware backend that can:

- receive Action Intents
- apply workflow and approval policy
- accept and track evidence metadata
- ingest and query kernel-aligned receipts
- expose audit and export surfaces

That is enough to prove the control-plane shape without over-claiming maturity in the more sensitive proof, key, or escrow domains.
