# Managed Signing Plan

## Purpose

This document defines how Actenon Cloud must move from development signing to production-grade managed signing.

## What Exists Today

- `SigningKeyReference`, `IssuedProof`, and `SigningOperationRecord` persistence exists.
- The issuance path is deterministic and auditable.
- Proofs bind to `action_intent_digest`, `audience`, `scope`, `nonce`, and `expires_at`.
- The implemented backend is development-local HMAC for local and test flows.
- The `external_managed` backend is now an intentional stub that fails clearly when selected.
- Receipt counter-signing is a separate implemented service with a
  provider-neutral HSM/KMS interface, Ed25519 public format compatibility,
  rotation, key-set publication, separation of duties, and audit records.

## What The Stub Means Today

- `external_managed` key references can be created and resolved
- the runtime records the attempted signing operation
- the signing call fails intentionally with a message pointing back to `app/services/signing.py`
- no KMS integration exists
- no HSM integration exists
- no asymmetric production issuer key flow exists

This is a truth-repair step, not production signing.

The stub described here applies to PCCB proof issuance. It does not apply to
`app/services/countersigning.py`. Receipt counter-signing has its own custody
and lifecycle boundary because it is a witness operation, not proof issuance.
See [docs/COUNTERSIGNING_SERVICE.md](docs/COUNTERSIGNING_SERVICE.md).

## Design-Partner Pilot Requirements

- move pilot issuance away from default local secrets
- use a dedicated pilot issuer identity and dedicated key reference records
- keep issuer metadata stable and documented for pilot consumers
- record signing operations and proof issuance decisions for every pilot action
- limit pilot trust claims to bounded proof issuance only, not verifier behavior

## Integration Seam

The production seam now lives in:

- `SigningService._sign_bytes(...)`
- `SigningService._sign_with_external_managed_backend(...)`

The current stub has access to the right inputs already:

- `SigningKeyReference.provider_key_ref`
- `SigningKeyReference.algorithm`
- `SigningKeyReference.public_key_ref`
- `IssuedProof`
- canonicalized payload bytes

That means the remaining work is adapter completion, not interface redesign.

## What Must Change For Production

- integrate managed KMS or HSM-backed signing
- keep raw key material outside the application process
- use asymmetric signing with explicit key versioning and rotation
- implement issuer trust metadata that matches real deployment domains and operational ownership
- add signing failure alerts, key disable flows, and revocation governance

## Minimum Completion Checklist

- map `provider_key_ref` to a real KMS or HSM key identifier
- call the managed signing provider with the canonical proof payload digest or message bytes
- translate provider responses into `signature`, `provider_operation_ref`, and clear failure detail
- enforce supported algorithm and key-backend combinations per provider
- record timeout, retry, and provider error behavior without silently retrying unsafe signing requests
- publish and maintain the verifier-facing public key material and issuer metadata outside this repo
- document key rotation, disable, and rollback procedures for hosted pilots

## Real Production Target

- managed KMS or HSM-backed signing
- non-exportable keys
- rotation and deactivation procedures
- auditable signing operations
- environment-specific issuer identities

The receipt counter-signing service supplies these application-level controls,
but production completion still requires a selected provider adapter, provider
IAM/key policy, immutable provider audit export, production HTTPS key
publication, and a rehearsed provider-backed recovery exercise.
