# OSS Trace Viewer

## What It Is

The OSS trace viewer is a read-only interface for inspecting kernel-native traces.

It exists to make the Action Control System Kernel easy to see, understand, and evaluate in practice. Instead of asking people to read only raw JSON, it gives them a clean way to inspect the artifacts that the kernel defines.

## What It Shows

The viewer should focus on a narrow, public-facing job:

- render an Action Intent
- render the linked receipt trail
- render the trace or event sequence that connects them
- render linked proof metadata when provided
- render verifier outputs when those outputs are supplied from the separate verifier repo or verifier interface

For the invoice payment example, that means someone should be able to open a trace and understand:

- what payment action was proposed
- what receipt came back
- how the linked trace moved from request to outcome
- what proof or verifier artifacts were attached to the trace bundle

## What It Does Not Do

The OSS trace viewer does not run the workflow around the trace.

It is not:

- an approval queue
- a policy editor
- an evidence workflow UI
- an audit operations dashboard
- a tenant admin console
- the operational product

It does not accept approvals, upload evidence, issue proofs, release capability, or manage live execution.

## Why It Is Read-Only

Read-only is not a limitation by accident. It is the product boundary.

The OSS viewer should be safe to share, easy to understand, and easy to trust. That is only true if it stays focused on rendering already-recorded artifacts rather than changing workflow state.

## Why This Strengthens The OSS Surface

The viewer strengthens OSS because it gives the kernel a visible, usable surface without forcing the OSS project to become a commercial operations product.

That is a healthy split:

- OSS shows the kernel clearly
- the paid layer handles live governance and operations

## Where The Paid Layer Starts

The paid Action Control Execution Layer UI starts when the user needs to act on live workflow state.

That includes:

- deciding whether an invoice payment should proceed
- reviewing approvals and evidence
- issuing or revoking proofs
- managing capability release
- handling receipt exceptions
- operating audit workflows
- administering tenant-scoped users and controls

The OSS trace viewer helps people understand the trace. The paid layer helps people run the workflow.

## Public Positioning Summary

The OSS trace viewer is the public, read-only window into kernel-native traces.

It makes the kernel tangible.

It does not replace the paid Action Control Execution Layer, and it should not be mistaken for the operational product.
