# Real Capability Release Plan

## Purpose

This document defines the path from the current simulated capability release path to a real protected-resource integration.

## What Exists Today

- Escrow records are persisted and bind back to issued proofs.
- Escrow supports `held`, `released`, `consumed`, `revoked`, `quarantined`, and `expired`.
- Transition history is durable and auditable.
- Release is tightly scoped to audience, scope, action hash, nonce, and expiry.

## What Is Simulated Today

- capability release returns a locally generated opaque token
- token custody is only simulated inside the service
- no external protected resource or provider broker is called
- provider execution updates are lifecycle hooks, not a hardened integration

## Design-Partner Pilot Requirements

- choose one protected resource pattern and document it clearly
- keep capability scope narrow and finance-focused
- require exact proof-to-release binding
- require manual operator visibility for revoke and quarantine paths
- record provider execution references even if downstream integration is still shallow

## What Must Change For Production

- replace development_simulated release with an external managed release backend
- integrate with a real protected resource or broker boundary
- ensure released capability material is single-use or strongly bounded
- support revoke and quarantine semantics that external systems can actually enforce
- add provider-side acknowledgement, failure handling, and reconciliation contracts

## Real Production Target

- external managed capability release
- provider acknowledgement and lifecycle callbacks
- enforceable revoke and quarantine semantics
- clear control-plane versus provider responsibility split
