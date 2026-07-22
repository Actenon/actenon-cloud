# OSS Trace Viewer Boundary

## Purpose

This document defines the scope of the open source trace viewer that belongs with the Action Control System Kernel.

Its job is simple: make kernel-native traces easy to inspect without turning the OSS surface into the paid operational product.

## Why The Viewer Belongs In OSS

The viewer belongs in OSS because it helps people understand and trust the kernel itself.

- The kernel publishes public contracts and public-facing trace shapes.
- Developers and design partners need a concrete way to inspect those artifacts.
- A read-only viewer makes the kernel tangible without requiring access to the paid control-plane product.
- The viewer helps adoption by turning raw trace bundles into something a human can read quickly.

In short: the viewer explains the kernel. It does not run the business workflow around the kernel.

## What The OSS Viewer Renders

The OSS viewer should render immutable or already-recorded artifacts such as:

- Action Intent payloads that follow the kernel contract
- receipt payloads that follow the kernel contract
- kernel-native trace bundles or event sequences
- linked proof artifacts or proof metadata when supplied as input
- verification outputs supplied by a separate verifier repo or verifier interface
- state progression that can be derived directly from the supplied trace data

The key rule is that the viewer renders supplied artifacts. It does not create or change them.

## What The OSS Viewer Does Not Do

The OSS viewer is not:

- an approval queue
- a policy editor
- an evidence workflow UI
- an audit operations dashboard
- a tenant admin console
- the operational product

It also does not:

- issue proofs
- verify proofs itself
- release capabilities
- trigger provider execution
- manage operators, tenants, or access control
- mutate workflow state

## Why It Must Be Read-Only

The viewer should be read-only for three reasons:

1. It keeps the public kernel surface safe and easy to reason about.
2. It preserves a clean boundary between public inspection and paid operations.
3. It avoids quietly growing into an operational workflow product.

If a UI action changes state, assigns work, approves a payment, edits policy, or releases a capability, it does not belong in the OSS trace viewer.

## How The Viewer Makes The Kernel Tangible

The kernel is most useful when people can see what it means in practice.

The OSS viewer makes that possible by turning:

- raw Action Intent JSON
- raw receipt JSON
- linked trace events
- linked proof metadata
- linked verifier outputs

into a human-readable trace of what happened.

That is valuable for:

- developers integrating the kernel
- reviewers debugging a trace bundle
- design partners evaluating the public kernel surface
- anyone trying to understand the shape of a governed execution trace without using the paid product

## Where The Paid UI Begins

The paid Action Control Execution Layer UI begins where authenticated operational workflow begins.

That includes:

- triaging live actions that need attention
- routing approvals
- collecting and reviewing evidence
- issuing proofs
- releasing or revoking capability
- operating receipt and reconciliation workflows
- reviewing audit operations across live customer activity
- managing tenant, user, and admin settings

The OSS viewer stops short of all of that. It shows what happened. The paid UI manages what happens next.

## Boundary Test

Use this rule when deciding where a feature belongs:

- If it helps someone inspect a completed or captured trace without changing anything, it likely belongs in the OSS viewer.
- If it helps someone operate, govern, approve, release, or administer live workflow state, it belongs in the paid layer.
