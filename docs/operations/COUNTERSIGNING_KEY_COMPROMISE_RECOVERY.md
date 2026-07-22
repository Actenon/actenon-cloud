# Counter-Signing Key Compromise Recovery

## Scope

Use this runbook when a receipt counter-signing key may have been exposed,
misused, incorrectly authorized, or controlled by a compromised service
identity. Treat uncertainty as compromise until disproved.

This runbook covers counter-signatures only. It does not revoke PCCBs, alter
protected-endpoint receipts, or establish whether a receipt is truthful.

## Roles

- Incident commander: coordinates and owns the timeline.
- KMS/HSM operator: executes approved provider lifecycle operations.
- Two security approvers: authorize rotation and revocation.
- Trust-anchor publisher: publishes and validates the public key set.
- Audit lead: preserves Cloud, provider, identity, and publication logs.
- Relying-party coordinator: sends notifications and verification guidance.

No individual should fill the KMS/HSM operator and both approval roles.

## Immediate Containment

1. Open a security incident and record the suspected `kid`, detection time,
   source, and confidence.
2. Disable the counter-signing runtime identity if active misuse may be
   continuing.
3. Preserve application signing records, provider sign logs, identity logs,
   key-policy history, and key-set publication history.
4. Stop automated counter-signing. Do not switch to local or exportable keys.
5. Identify the earliest potentially compromised time. This becomes the
   conservative `revoked_at` unless evidence supports an earlier boundary.

## New-Key Standup

1. Create a lifecycle request for a new unique `kid`.
2. Obtain two independent approvals.
3. Provision a non-exportable Ed25519 key in the HSM/KMS.
4. Publish a key set containing:
   - the new key as `active`
   - previous uncompromised keys as `retired`
   - the suspected key as historical with the chosen `revoked_at`
5. Fetch the well-known key set over its public HTTPS origin.
6. Pin the fetched digest and verify publication consistency.
7. Sign a non-production test receipt digest with the new key.
8. Verify that artifact offline with the open-source verifier and fetched key set.
9. Restore the runtime identity with sign permission on the new key only.

## Compromised-Key Treatment

1. Disable the suspected provider key through the quorum-approved lifecycle path.
2. Publish `revoked_at` and a bounded revocation reason.
3. Confirm the provider rejects new sign requests for the old key.
4. Query all application and provider signing events for the affected `kid`.
5. Classify artifacts:
   - before the conservative compromise boundary
   - at or after the boundary
   - timestamp or provenance uncertain
6. Do not silently re-sign affected historical artifacts. Preserve the original
   artifact and attach explicit investigation or replacement evidence.

The public verifier accepts a historical signature only when `signed_at` is
strictly before `revoked_at`. Relying parties may apply stricter local policy.

## Relying-Party Notification

Notify affected relying parties with:

- witness identity and affected `kid`
- conservative compromise and revocation times
- new active `kid`
- HTTPS key-set location and pinned digest
- artifact population under review
- recommended cache refresh and local policy action
- incident contact and next update time

Do not state that prior artifacts are safe merely because their signatures
verify. Signature validity and receipt truth are separate questions.

## Recovery Verification Checklist

- [ ] Automated signing paused during containment.
- [ ] Logs and key-policy history preserved.
- [ ] New non-exportable key provisioned under a new `kid`.
- [ ] Two independent approvals recorded.
- [ ] New public key published before activation.
- [ ] Old and new non-compromised artifacts verify with the published key set.
- [ ] Suspected key disabled at the provider.
- [ ] `revoked_at` published and externally fetched.
- [ ] Post-revocation signatures under the old `kid` are rejected.
- [ ] Runtime identity can sign only with the new key.
- [ ] Relying parties notified.
- [ ] Incident timeline, affected artifacts, and follow-up actions recorded.

## Rehearsal Cadence

Run this procedure at least twice per year and after any provider, IAM,
publication, or verifier-format change. A production rehearsal must use the
real managed provider and publication origin while signing only synthetic test
digests.

The local throwaway-key rehearsal evidence is recorded in
[COUNTERSIGNING_RECOVERY_DRY_RUN_2026-06-06.md](evidence/COUNTERSIGNING_RECOVERY_DRY_RUN_2026-06-06.md).
