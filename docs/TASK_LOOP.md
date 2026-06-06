# Task Loop

## Purpose

This document defines the default delivery loop for Actenon Cloud so changes remain spec-driven, kernel-aligned, and acceptance-gated.

## Standard Delivery Loop

1. Clarify the problem and whether it belongs to the control plane, the open kernel, or the contract boundary between them.
2. Update the relevant specification documents before or alongside code changes.
3. Add or update schemas, tests, and acceptance checks for the intended behavior.
4. Implement the smallest backend-first slice that satisfies the updated spec.
5. Run `bash scripts/verify.sh`.
6. Run `bash scripts/judge.sh`.
7. Record any gaps, deferred work, or assumptions directly in repository docs.

## Kernel Alignment Loop

Use this loop whenever the open execution kernel changes:

1. Identify which published kernel artifact changed and which control-plane surfaces depend on it.
2. Pin the new kernel artifact version or reference in the appropriate dependency location.
3. Update contract tests and schema mirrors or imports as needed.
4. Re-run the full acceptance gate.
5. Reject the update if it forces the control plane to invent local semantics that belong in the kernel.

## Feature Delivery Rules

- Start with API and workflow behavior, not UI behavior.
- Prefer versioned schemas and explicit state transitions over implicit conventions.
- Keep approval, evidence, and audit records linked by durable identifiers.
- Treat key lifecycle, proof issuance, and escrow changes as high-risk and require stronger review.

## Definition Of Done For Individual Tasks

A task is not done unless:

- the repository docs still match reality
- required tests or acceptance checks exist
- the control-plane versus kernel boundary remains clear
- new behavior is observable and auditable
- deferred risks are written down explicitly

## When To Stop And Re-Scope

Stop and re-scope if a task starts to:

- re-implement kernel execution or verifier logic
- introduce major UI work before backend surfaces stabilize
- require an unvalidated kernel contract assumption
- bundle multiple platform domains into one change without clear acceptance criteria
