# Operated Transparency Log

## Purpose

Actenon Cloud operates an append-only Merkle log for Actenon Receipt digests.
The service stores digests only, publishes signed checkpoints, and serves the
open P11 inclusion and consistency proof formats.

A relying party can verify every output with the open Actenon SDK and pinned
public keys. The Cloud service is the operator, not the verification authority.

Public format and verifier:

- <https://github.com/Actenon/actenon/blob/main/spec/transparency-log/SPEC.md>
- <https://github.com/Actenon/actenon/blob/main/actenon/verifier/transparency.py>

## Stored Data

`transparency_log_leaves` contains:

- log identifier
- append index
- Receipt artifact digest
- RFC 6962 leaf hash
- append-chain hash
- ingestion timestamp

It does not contain Receipt payloads, tenant payloads, evidence, action
parameters, credentials, or private keys.

`transparency_checkpoint_records` contains the public checkpoint artifact,
selected `kid`, provider operation reference, checkpoint digest, predecessor
checkpoint digest, actor, status, and timestamps.

## Append And Checkpoint Flow

1. An authenticated platform operation submits a `sha-256` / `RFC8785-JCS`
   Receipt digest.
2. The database log-state row is locked.
3. The digest is assigned the next immutable leaf index.
4. A domain-separated leaf hash and linked append-chain hash are stored in the
   same transaction.
5. Before checkpoint publication, the service recomputes the append chain,
   Merkle roots, checkpoint links, and monotonic state.
6. The service builds the exact public P11 checkpoint statement.
7. `CounterSigningService` sends the canonical statement bytes to the managed
   HSM/KMS provider under the active `kid`.
8. The signed public checkpoint and provider audit reference are committed.

The checkpoint runtime requires the dedicated
`transparency_log.checkpoint.sign` permission. It does not receive raw private
key material or key-lifecycle permissions.

## Key Discovery

The managed P10 key registry publishes historical and active public keys by
`kid`. Keys used by this operated witness declare both:

- `receipt_countersignature`
- `transparency_checkpoint`

The protocols use different signed contexts. Historical keys remain available
so older checkpoints continue to verify after rotation.

## API Surface

Authenticated platform operations:

```text
POST /api/v1/transparency/logs/{log_id}/digests
POST /api/v1/transparency/logs/{log_id}/checkpoints
GET  /api/v1/transparency/logs/{log_id}/integrity
```

Public witness and relying-party operations:

```text
GET /api/v1/transparency/logs/{log_id}/checkpoints
GET /api/v1/transparency/logs/{log_id}/checkpoints/latest
GET /api/v1/transparency/logs/{log_id}/proofs/inclusion
GET /api/v1/transparency/logs/{log_id}/proofs/consistency
GET /api/v1/transparency/logs/{log_id}/monitor
```

The read endpoints expose only public verification artifacts and digests.

## Independent Monitoring

An external monitor must persist its last verified checkpoint and call the
public `verify_monitor_update` routine before accepting a newer checkpoint.
Monitors should compare `(log identity, tree size, root hash)` with other
witnesses. A smaller tree is rewind evidence. Two valid signed roots at the same
size are split-view evidence.

The service exposes the previous checkpoint, current checkpoint, and
consistency proof together through the monitor endpoint. No trust in the
service's conclusion is required.

## Integrity Controls

The service enforces:

- unique leaf index and Receipt digest per log
- a locked monotonic next-index record
- a linked append-chain commitment over every stored digest
- unique checkpoint tree size per log
- linked checkpoint digests
- pre-publication recomputation of every persisted leaf and checkpoint root
- fail-closed managed signing
- public verification against the published key set

Internal checks cannot detect a complete database-and-state rollback to a
self-consistent older snapshot. Externally persisted checkpoints and
consistency verification are the control for that threat.

## Metrics

The runtime emits:

- `action_control_plane_transparency_log_leaves_total`
- `action_control_plane_transparency_checkpoints_total`
- `action_control_plane_transparency_tree_size`
- `action_control_plane_transparency_integrity_failures_total`

Alert immediately on any integrity failure, checkpoint-signing failure,
decrease observed by a monitor, same-size root disagreement, or checkpoint
publication gap beyond the deployment's agreed cadence.

## Claim Boundary

Verification proves that a trusted checkpoint key signed a tree state and that
the supplied proofs are consistent with that state. It does not prove that a
Receipt is truthful, that every Receipt was submitted, that the service was
always available, or that no split view exists without independent checkpoint
comparison.

Operational response is defined in
[TRANSPARENCY_LOG_INTEGRITY_RUNBOOK.md](operations/TRANSPARENCY_LOG_INTEGRITY_RUNBOOK.md).
