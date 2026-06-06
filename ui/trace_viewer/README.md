# OSS Trace Viewer Package Scope

This path documents the intended scope of the OSS trace viewer.

The actual viewer belongs in the separate open kernel repository, not in the private control-plane repository.

## Package Purpose

The OSS trace viewer should provide a clean, public, read-only interface for rendering kernel-native traces.

Its purpose is to help developers, reviewers, and design partners inspect:

- Action Intent artifacts
- receipt artifacts
- trace bundles
- linked proof metadata
- verifier outputs provided by the separate verifier repo or verifier interface

## Package Non-Goals

This package is not:

- an approval queue
- a policy editor
- an evidence workflow UI
- an audit operations dashboard
- a tenant admin console
- the operational product

It should not include write paths for approvals, evidence, policy, proof issuance, capability release, or tenant administration.

## Why Read-Only Matters

Read-only keeps the package aligned with the OSS boundary:

- it explains kernel traces
- it does not operate customer workflow
- it stays separate from the paid Action Control Execution Layer UI

## Read Next

- [TRACE_VIEWER.md](../../TRACE_VIEWER.md)
- [TRACE_VIEWER_BOUNDARY.md](../../TRACE_VIEWER_BOUNDARY.md)
- [REPO_BOUNDARY.md](../../REPO_BOUNDARY.md)
