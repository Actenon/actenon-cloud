# Capability Escrow

## Purpose

This document defines the initial Capability Escrow implementation in Actenon Cloud.

The escrow service is a control-plane custody layer that releases narrowly scoped capability only after a valid proof has already been issued. It does not execute finance actions itself and it does not replace provider or kernel execution authority.

## Scope In This Pass

Implemented now:

- durable `EscrowRecord` persistence bound one-to-one to an `IssuedProof`
- tightly scoped capability release using the proof's exact `audience`, `scope`, `scope_hash`, `action_intent_digest`, and `nonce`
- lifecycle transitions for `held`, `released`, `consumed`, `revoked`, `quarantined`, and `expired`
- durable `EscrowTransitionRecord` history for every lifecycle change
- protected-resource execution update hooks that record coarse execution observation after consumption
- development-local simulated release mode with honest behavior and explicit limits

Not implemented in this pass:

- real provider execution
- external managed capability brokers
- receipt-bound release rules
- proof revocation APIs
- multi-step provider adapters or callback automation beyond lifecycle recording

## Boundary

Capability Escrow sits between proof issuance and downstream protected resources.

It owns:

- whether a released capability exists
- how that capability is bounded
- whether the capability has been consumed, revoked, quarantined, or expired
- control-plane observation of coarse execution progress after consumption

It does not own:

- verifier logic
- kernel execution semantics
- provider-specific execution guarantees
- final receipt truth

## Preconditions For Hold Creation

An escrow hold can only be created when:

- the referenced `IssuedProof` exists
- the proof is in `issued` status
- the proof has not expired
- the proof has not been revoked

The escrow record copies the proof binding fields and never widens them.

## Release Model

### Development Simulated

The implemented release backend is `development_simulated`.

Behavior:

- generates an opaque capability token at release time
- stores only a digest of that token
- returns the raw token exactly once in the release response
- records that the release is simulated and no external provider integration occurred

This is real control-plane lifecycle behavior for local and test environments. It is not a claim that development-local capability release is suitable for production finance use.

### External Managed

`external_managed` is modeled in config and data types, but not implemented.

If configured, release requests fail honestly rather than pretending a managed broker, KMS, or provider adapter exists.

## Finance-Focused Capability Shape

Release 1 uses finance-oriented capability labels such as:

- `finance.transfer.release`
- `finance.payout.release`
- `finance.payment.release`

The protected resource is recorded separately as `protected_resource_ref`, for example a provider endpoint, treasury rail, or internal execution surface.

## API Surface

### `POST /api/v1/escrow/holds`

Creates or replays an escrow hold for an issued proof.

### `POST /api/v1/escrow/{escrow_record_id}/release`

Releases a capability from hold and returns the one-time raw token in development-local mode.

### `POST /api/v1/escrow/{escrow_record_id}/consume`

Consumes a released capability using the raw token and moves execution observation to `dispatch_requested`.

### `POST /api/v1/escrow/{escrow_record_id}/revoke`

Revokes a held or released capability before it is consumed.

### `POST /api/v1/escrow/{escrow_record_id}/quarantine`

Freezes a capability path for investigation, including consumed paths.

### `POST /api/v1/escrow/{escrow_record_id}/execution-updates`

Records observed execution progress after consumption.

### `GET /api/v1/escrow`

Lists escrow records with optional filters.

### `GET /api/v1/escrow/{escrow_record_id}`

Returns a single escrow record with transition history.

## Persistence Model

`EscrowRecord` persists:

- linkage to tenant, Action Intent, and issued proof
- bounded capability fields copied from the proof
- release mode
- escrow status
- coarse execution state
- protected resource reference
- capability reference and token digest
- provider correlation fields
- revocation and quarantine metadata
- expiry timestamps

`EscrowTransitionRecord` persists:

- transition type
- before and after escrow status
- before and after execution state
- actor identity
- optional reason code and detail
- transition metadata

## Deterministic State Rules

- Hold creation is idempotent for the same issued proof plus the same capability and protected resource.
- A released capability cannot be released again because the raw token is only emitted once.
- Only a released capability can be consumed.
- Only held or released capability can be revoked.
- Quarantine can freeze held, released, or consumed capability.
- Execution updates are allowed only after consumption.
- Escrow capability expiry cannot exceed the proof expiry or the configured escrow TTL cap.

## Future Work

Later passes should add:

- receipt-aware release gates
- escrow-backed proof revocation and invalidation propagation
- external managed capability release integrations
- richer provider callback correlation
- audit API surfacing over escrow transitions
