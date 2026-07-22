# Open Kernel Dependency Model

## Purpose

This document defines how Actenon Cloud should depend on the separate open execution kernel without replacing it.

## Current Assumptions

The kernel repository is not present in this workspace, so the dependency model below describes the required posture rather than a validated implementation. The control plane should depend on published, versioned kernel artifacts once those artifacts and publication mechanics are confirmed.

## Ownership Boundary

| Domain | Open Execution Kernel | Actenon Cloud |
| --- | --- | --- |
| Execution runtime | Owns | Does not own |
| Verifier and proof semantics | Owns | Must consume, not redefine |
| Action admission and tenant APIs | Does not own | Owns |
| Policy and approval workflows | Does not own | Owns |
| Evidence custody and retention controls | Does not own | Owns |
| Receipt storage, indexing, and query APIs | Publishes canonical artifacts | Owns ingestion and access surfaces |
| PCCB and proof issuance workflow | Supplies underlying outputs and semantics | Owns orchestration, packaging, and policy gating |
| Signing and key lifecycle | May provide proof-related primitives | Owns managed key orchestration and enterprise controls |
| Capability Escrow | Does not own | Owns |
| Revocation and quarantine workflows | May emit relevant signals | Owns policy and customer-facing actions |

## Preferred Dependency Shape

The control plane should adopt kernel artifacts through explicit version pinning rather than copy-pasting logic. The preferred order of dependency mechanisms is:

1. Published kernel packages or artifacts containing schemas, interface definitions, and compatibility metadata
2. Immutable release assets or tagged references
3. Immutable commit references as a temporary fallback

The control plane should not vendor large portions of kernel source code unless there is no safer option and the exception is documented.

## Expected Contract Families

The exact artifact set must be confirmed with the kernel repository. Likely contract families include:

- receipt schemas
- proof or verifier output envelopes
- execution outcome status models
- adapter callback or orchestration boundary definitions
- revocation or invalidation signals emitted by kernel-side processes

These are examples, not validated facts about the kernel's current publication model.

## Compatibility Rules

- Every kernel dependency must be pinned to an immutable version reference.
- Contract compatibility checks should run in `scripts/verify.sh` once kernel artifacts are integrated.
- The control plane may extend its own metadata around kernel artifacts, but must preserve canonical kernel fields and semantics.
- Breaking kernel changes must fail acceptance until the control plane is updated or the dependency is rolled back.

## What This Repo Must Never Do

- Re-implement verifier logic that belongs in the kernel
- Invent alternate kernel receipt semantics for convenience
- Modify canonical kernel artifacts in place before storage or export
- Hide kernel compatibility drift behind unchecked translation layers

## Near-Term Repository Implication

`schemas/kernel/` should eventually hold imported or pinned kernel-facing schemas or references to them. `schemas/control_plane/` should hold schemas owned by this repository. That physical split is how the repository will make ownership visible in day-to-day development.
