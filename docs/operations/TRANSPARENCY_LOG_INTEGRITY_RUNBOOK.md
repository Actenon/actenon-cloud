# Transparency Log Integrity Runbook

## Trigger Conditions

Start this runbook for any of the following:

- internal integrity report returns `ok: false`
- checkpoint signing or publication fails repeatedly
- an external monitor reports rewind
- two valid signed checkpoints have the same log and tree size but different
  roots
- a consistency proof fails between previously accepted checkpoints
- database restore would move the log behind an externally observed checkpoint
- leaf index, append-chain, checkpoint-link, or root drift is detected

Treat split-view or rewind evidence as a security incident. Do not dismiss it as
a cache problem until the signed artifacts have been compared.

## Immediate Containment

1. Stop digest ingestion and checkpoint publication.
2. Preserve the database, application logs, HSM/KMS sign logs, public key-set
   versions, published checkpoints, and proof responses.
3. Record the last checkpoint independently verified by each known monitor.
4. Disable the checkpoint-signing runtime identity if unauthorized signing is
   possible.
5. Do not delete, overwrite, or re-sign conflicting checkpoints.
6. Page the incident commander, transparency-log operator, signing custodian,
   database operator, and relying-party coordinator.

## Triage

1. Verify each disputed checkpoint signature with the pinned public key set.
2. Compare log identity, `kid`, tree size, root hash, and issued timestamp.
3. Verify the consistency proof from the last trusted checkpoint.
4. Run the authenticated integrity endpoint.
5. Compare database leaf count and latest checkpoint state with the external
   monitor's last accepted size.
6. Correlate checkpoint records with provider operation references and HSM/KMS
   audit logs.
7. Determine whether the failure is:
   - unavailable proof generation
   - stale publication
   - local database corruption
   - incomplete restore
   - unauthorized checkpoint signing
   - signed equivocation or rewind

## Restore Safety

Never resume from a database snapshot whose tree size is below any externally
observed valid checkpoint.

For an eligible restore:

1. Keep publication frozen.
2. Restore into an isolated environment.
3. Recompute every leaf hash, append-chain hash, checkpoint root, checkpoint
   digest, and checkpoint predecessor link.
4. Verify the restored latest checkpoint against the public SDK and key set.
5. Generate and verify consistency from every retained externally trusted
   checkpoint to the candidate current checkpoint.
6. Resume only after security and database operators record joint approval.

If no retained state extends the last externally observed checkpoint, do not
silently start a replacement history under the same log identity. Create an
incident record, notify relying parties, and use a new explicitly versioned log
identity if recovery policy requires a fresh log.

## Equivocation Response

When two valid signed same-size checkpoints have different roots:

1. Preserve both artifacts and their retrieval metadata.
2. Disable checkpoint signing.
3. Revoke or rotate the affected `kid` using the counter-signing key recovery
   process if key misuse is suspected.
4. Publish an incident notice containing both checkpoint coordinates and the
   affected `kid`; do not publish sensitive Receipt payloads.
5. Ask independent monitors to retain and exchange the conflicting artifacts.
6. Identify all checkpoints and counter-signatures issued after the earliest
   conflicting size.
7. Do not claim that one branch is authoritative until the incident review
   establishes provenance.

## Recovery Verification

- [ ] Ingestion and publication were frozen during investigation.
- [ ] External monitor checkpoints were preserved.
- [ ] Database and HSM/KMS audit logs were preserved.
- [ ] Every retained checkpoint verifies with the public SDK.
- [ ] Consistency verifies from the last externally trusted checkpoint.
- [ ] No same-size conflicting signed root remains unexplained.
- [ ] The active signing identity and `kid` have the intended permissions.
- [ ] Public key discovery includes required historical keys.
- [ ] Relying parties received the incident and recovery coordinates.
- [ ] Monitoring resumed before publication resumed.

## Required Monitoring

At least two independently operated monitors should:

- fetch checkpoints from separate network paths where practical
- persist the last verified checkpoint durably
- verify every forward consistency proof
- reject rewind and same-size root changes
- exchange checkpoint coordinates with another monitor
- alert when publication exceeds the agreed maximum interval

An operator-side integrity check is useful but is not an independent witness.
