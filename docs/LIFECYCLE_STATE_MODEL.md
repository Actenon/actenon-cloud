# Lifecycle State Model

## Purpose

This document defines the implemented control-plane lifecycle axes around Action Intent intake, proof issuance, capability escrow, and coarse execution observation.

## Why Separate Axes

The control plane must not collapse policy, approval, proof, and execution into one overloaded status.

Release 1 keeps these concerns separate:

- `decision_state` answers what the deterministic intake policy said
- `approval_state` answers whether human or delegated approval completed
- `evidence_state` answers whether required evidence is currently satisfied
- `proof.status` answers whether a bounded proof was issued
- `escrow.status` answers whether a released capability is held, released, consumed, revoked, quarantined, or expired
- `execution_state` answers the coarse control-plane observation of release and downstream execution progress

## Implemented Decision States

The Action Intent intake path currently uses:

- `allow`
- `deny`
- `approval_required`
- `needs_evidence`
- `structurally_non_executable`

These states are about admission and workflow requirements, not downstream execution.

## Implemented Approval States

The Action Intent record aggregates approval progress as:

- `not_started`
- `not_required`
- `pending`
- `satisfied`
- `rejected`
- `expired`
- `canceled`

## Implemented Evidence States

The Action Intent record aggregates evidence progress as:

- `not_required`
- `pending`
- `satisfied`
- `expired`
- `canceled`

## Implemented Proof States

The issued proof record uses:

- `requested`
- `issued`
- `rejected`
- `failed`
- `revoked`
- `expired`

## Implemented Escrow States

The escrow record uses:

- `held`
- `released`
- `consumed`
- `revoked`
- `quarantined`
- `expired`

These are custody and release states for the capability itself.

## Implemented Execution States

The Action Intent and escrow record both use the same coarse execution-state vocabulary:

- `not_requested`
- `capability_held`
- `capability_released`
- `dispatch_requested`
- `dispatch_confirmed`
- `result_observed`
- `failure_observed`
- `revoked`
- `quarantined`
- `expired`

This axis is a control-plane mirror only. It does not redefine kernel execution semantics.

## State Mapping By Operation

### Hold Creation

- `escrow.status=held`
- `execution_state=capability_held`

### Capability Release

- `escrow.status=released`
- `execution_state=capability_released`

### Capability Consumption

- `escrow.status=consumed`
- `execution_state=dispatch_requested`

### Protected Resource Execution Update

The capability remains `consumed` while execution observation can advance to:

- `dispatch_confirmed`
- `result_observed`
- `failure_observed`

### Revocation

- `escrow.status=revoked`
- `execution_state=revoked`

### Quarantine

- `escrow.status=quarantined`
- `execution_state=quarantined`

### Expiry

- `escrow.status=expired`
- `execution_state=expired`

Expiry currently applies to held or released capability that ages out before consumption.

## Mirroring Onto Action Intent

`ActionIntentRecord.execution_state` is a coarse mirror of the latest relevant escrow or execution observation for that intent.

It is intentionally not:

- a kernel execution ledger
- a receipt state
- proof validity
- audit history

The durable history lives in `EscrowTransitionRecord` and the other domain records.

## Release 1 Limits

Release 1 intentionally does not model:

- full provider execution state machines
- receipt-driven lifecycle completion
- cross-provider compensation flows
- proof revocation cascading into receipt and escrow controls

Those remain later layers on top of this narrower control-plane state model.
