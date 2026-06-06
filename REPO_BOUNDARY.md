# Repo Boundary

## Purpose

This document states the boundary of the Actenon Cloud repository in plain terms.

It is the source-of-truth positioning summary for what this repo owns versus what remains outside this repo.

## What This Repo Is

Actenon Cloud is the private commercial control-plane and execution-control-layer repository.

It governs and records finance-focused execution decisions. It does not define low-level execution semantics and it does not perform proof verification.

## What This Repo Owns

This repo owns:

- tenant-scoped Action Intent intake
- deterministic policy evaluation
- approval workflow and evidence linkage
- proof issuance orchestration and signing records
- capability escrow lifecycle state
- receipt ingestion, reconciliation, and audit traces
- tenancy, admin, and early auth foundations

This repo may issue proofs, store proof records, and expose proof-related workflow state.

## What The Separate Open Kernel Repo Owns

The separate open kernel repo owns:

- canonical public contracts consumed by this repo, including Action Intent and receipt families
- execution-side semantics
- low-level execution and adapter contracts
- execution-side state that the control plane must consume rather than redefine
- a public read-only trace viewer for kernel-native artifacts and trace bundles

## What The Separate External Verifier Repo Owns

The separate external verifier repo or verifier interface owns:

- proof verification logic
- proof validation semantics
- verifier-side interpretation of whether an issued proof is valid
- any verification outputs or attestations consumed by surrounding systems

## What This Repo Explicitly Does Not Own

This repo does not own:

- verifier implementation
- proof validation semantics
- real provider settlement truth
- payment-network execution guarantees
- finished provider or broker execution infrastructure

## Practical Rule

If a feature requires re-implementing verifier logic, it does not belong in this repository.

If a feature requires control-plane governance, approval, custody, release-state tracking, receipt indexing, or audit traceability around an external workflow, it likely does belong here.

## Pilot Interpretation

For the invoice payment execution pilot:

- this repo governs the payment decision flow
- this repo issues bounded proofs
- this repo records release state and receipts
- a public OSS trace viewer may render the resulting kernel-native trace artifacts in read-only form
- proof verification, if required, remains external to this repo

## Read Alongside

- [README.md](README.md)
- [EXTERNAL_DEPENDENCIES.md](EXTERNAL_DEPENDENCIES.md)
- [INTEGRATION_ASSUMPTIONS.md](INTEGRATION_ASSUMPTIONS.md)
