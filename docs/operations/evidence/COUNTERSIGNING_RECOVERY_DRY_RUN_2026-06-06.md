# Counter-Signing Recovery Dry Run: 2026-06-06

## Classification

Deterministic local rehearsal using throwaway Ed25519 keys. This is not evidence
of a production HSM/KMS ceremony or a live relying-party notification.

## Objective

Exercise the format-compatible recovery path:

1. provision initial non-exportable-key fixture
2. counter-sign a synthetic receipt digest
3. rotate to a new `kid`
4. verify old and new artifacts with one published historical key set
5. disable the old provider key
6. publish `revoked_at`
7. confirm a pre-revocation artifact remains verifiable
8. confirm application signing and lifecycle audit records exist

## Command

```bash
python -m pytest tests/integration/test_counter_signing_service.py -q
```

## Result

Date: 2026-06-06  
Result: PASS  
Tests: 6 passed

Observed controls:

- generated artifacts verified with the public
  `actenon.verifier.verify_countersignature` implementation
- the old `kid` remained available as a retired historical public key after rotation
- the new `kid` was active for new signatures
- a simulated compromise disabled the old provider key and published `revoked_at`
- a human signing attempt was denied before the provider sign call
- signing and lifecycle operations were recorded
- self-approval and insufficient lifecycle quorum were denied
- no private JWK field was published or persisted by the Cloud service
- a provider response containing private JWK material was rejected
- a key-set publication failure left no active database key and was audited

## Gaps Before Production Rehearsal

- connect the provider adapter to the selected production HSM/KMS
- validate provider IAM and non-exportability with provider-native evidence
- connect key-set publication to the production HTTPS origin
- exercise real cache invalidation and relying-party notification channels
- export provider and application audit logs to the immutable audit destination
- rehearse on-call detection, escalation, and communications timing

## Sign-Off

Engineering rehearsal evidence only. Security and operations sign-off remains
required after the production-provider dry run.
