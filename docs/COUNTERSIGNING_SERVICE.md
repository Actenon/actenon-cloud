# Receipt Counter-Signing Service

## Purpose

Actenon Cloud can counter-sign the canonical digest of an Actenon Receipt using
the open `receipt_countersignature v1` format. A relying party can verify the
artifact offline with the public Actenon verifier and a pinned public key set.

This service witnesses a receipt digest. It does not re-authorize the action,
prove the receipt is truthful, or replace execution-boundary verification.

Public format and verifier:

- <https://github.com/Actenon/actenon/blob/main/spec/countersignature/SPEC.md>
- <https://github.com/Actenon/actenon/blob/main/actenon/verifier/countersignature.py>

## Custody Boundary

Production construction requires `HsmKmsCounterSigningProvider` backed by a
`NonExportableEd25519Client`.

The client surface deliberately exposes only:

- create a non-exportable Ed25519 key
- return public JWK metadata and opaque provider references
- sign supplied bytes inside the HSM or KMS
- disable a provider key

There is no private-key export method. `HsmKmsCounterSigningProvider` rejects a
provider response that is exportable or contains private JWK fields. The
application database stores public JWKs, provider references, lifecycle
metadata, signatures, and audit records only.

Provider adapters must configure hardware or managed-key policy so raw private
key material cannot be returned to the service identity or a human operator.
The Python interface is a guardrail, not a substitute for provider IAM and key
policy.

## Signed Format

`CounterSigningService.counter_sign(...)`:

1. resolves or computes `SHA-256(RFC8785-JCS(receipt))`
2. builds the public v1 domain-separated statement
3. sends only the canonical statement bytes to the managed provider
4. emits an EdDSA artifact containing the active `kid`
5. records the request, actor, digest, provider operation reference, result,
   and public artifact

The service uses RFC 8785 canonicalization through the `rfc8785` package. Its
regression test verifies generated artifacts with the open-source
`verify_countersignature` implementation.

## Signing Authority

Only a principal with:

- `principal_type: service`
- `counter_signature.sign`

may request a counter-signature. A human user is denied even if a permission
claim is mistakenly attached. Denied attempts are recorded and never reach the
managed provider.

The service identity should have provider permission to sign with the active
counter-signing key only. It should not have permission to create, rotate,
disable, delete, export, or change key policy.

## Lifecycle Separation Of Duties

Provision, rotation, and revocation require:

- one authenticated human requester with the operation-specific permission
- at least two different authenticated human approvers with
  `counter_signature.keys.approve`
- requester/approver separation

Recommended provider IAM separates these roles:

| Role | Cloud permission |
| --- | --- |
| Counter-signing runtime | Sign with active key only |
| Key lifecycle automation | Create/disable key after approved workflow |
| Security requester | Submit lifecycle request only |
| Security approvers | Approve lifecycle request only |
| Audit reader | Read immutable signing and provider audit logs |

No role should combine runtime signing, lifecycle approval, and audit-log
administration.

## Rotation Sequence

`rotate_key(...)` uses this order:

1. validate quorum and requester separation
2. provision a new non-exportable Ed25519 key with a new `kid`
3. construct a key set containing the new active key and historical retired keys
4. atomically publish the versioned key set and well-known current document
5. mark the old key retired and the new key active in the control database
6. record provider and publication references

Publication happens before database activation. Therefore the runtime does not
begin using a new `kid` before relying parties can obtain its public key.
Historical public keys remain published with their original `kid`, so older
artifacts continue to verify.

The operated transparency log uses a separately authorized checkpoint-signing
operation on the same managed custody boundary. Published key descriptors may
therefore declare both `receipt_countersignature` and
`transparency_checkpoint`; the signed contexts remain domain-separated. See
[TRANSPARENCY_LOG_SERVICE.md](TRANSPARENCY_LOG_SERVICE.md).

`AtomicFileKeySetPublisher` writes:

```text
<publication-root>/.well-known/actenon/keys.json
<publication-root>/versions/<version>.json
```

The publication root must be deployed through an authenticated HTTPS origin.
Production object-storage/CDN publishers should implement the same
`KeySetPublisher` contract with immutable version objects and an atomic current
pointer.

## Failure Behavior

- HSM/KMS sign error: no artifact is emitted; operation is recorded failed.
- Unauthorized signing request: no provider call; operation is recorded denied.
- Key publication error: the new key is not activated in the control database.
- Database failure after publication: the published set safely contains the new
  public key, but the old retired key remains valid for verification. Operators
  must reconcile and retry the idempotent lifecycle operation.
- Disabled active key: signing fails closed until a new active key is published
  and activated.

Provider errors are stored by class, not raw response body, to avoid putting
provider-sensitive detail into application audit records.

## Audit Records

`counter_signing_operation_records` records every accepted or denied signing
request with:

- actor type and identifier
- receipt and signing-input digests
- selected `kid`
- status
- provider operation reference
- emitted public artifact
- timestamps and bounded failure code

`counter_signing_lifecycle_records` records:

- operation type
- target and prior `kid`
- requester and approvers
- provider operation reference
- published key-set digest and location
- status and timestamps

Provider-native HSM/KMS audit logs must also be retained in an immutable log
destination and correlated using the provider operation reference.

## Required Monitoring

Alert on:

- any denied human signing attempt
- provider signing failures or latency changes
- more than one active database key
- key-set publication failure
- key-set digest drift between origin and control record
- use of a retired or disabled provider key
- lifecycle requests without the configured quorum
- provider IAM or key-policy changes

See [COUNTERSIGNING_KEY_COMPROMISE_RECOVERY.md](operations/COUNTERSIGNING_KEY_COMPROMISE_RECOVERY.md)
for compromise handling.
