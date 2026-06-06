# Acceptance Criteria

This document defines acceptance for two layers:

- the repository bootstrap created in this pass
- the first product release that should be built on top of it

`scripts/verify.sh` is the source-of-truth gate for bootstrap acceptance and should expand over time into the main repository acceptance entrypoint.

## Repository Bootstrap Acceptance

The repository bootstrap is accepted only if all of the following are true:

1. The required top-level files exist:
   - `README.md`
   - `REPO_BOOTSTRAP_PLAN.md`
   - `docs/VISION.md`
   - `docs/ACCEPTANCE_CRITERIA.md`
   - `docs/TEST_PLAN.md`
   - `docs/ARCHITECTURE.md`
   - `docs/TASK_LOOP.md`
   - `docs/OPEN_KERNEL_DEPENDENCY_MODEL.md`
   - `scripts/verify.sh`
   - `scripts/judge.sh`
2. The repository contains clean directories for `app/`, `tests/`, `scripts/`, `docs/`, `schemas/`, `migrations/`, and `examples/`.
3. The documentation explicitly states that this repository is the control plane above the open execution kernel and is not the kernel or verifier repo.
4. The documentation clearly distinguishes which responsibilities belong to the kernel versus the control plane.
5. The first release scope is defined narrowly and honestly.
6. The repository posture is backend-first and does not overdesign a UI.
7. `scripts/verify.sh` fails when required artifacts are missing or when the core boundary sections are absent.
8. `scripts/judge.sh` summarizes whether the repository matches the current spec by invoking `scripts/verify.sh`.

## First Release Acceptance

The first release should be accepted only if all of the following are true:

### Action Intent Intake

- The service exposes a tenant-scoped API to submit Action Intents.
- Intake requests are validated against repo-owned control-plane schemas.
- Intake supports idempotent submission semantics.
- Every accepted intent receives an immutable identifier and audit trail.

### Tenant, Auth, And Admin Foundations

- Tenant boundaries are explicit and enforced on every write and read path.
- Authentication and authorization exist for administrators, operators, and service integrations.
- Administrative changes are auditable.

### Workflow Policy And Approval Engine

- Tenant and workflow policy definitions are versioned.
- Approval requirements are machine-evaluable and traceable.
- Approval decisions are recorded with actor, timestamp, and policy context.
- Workflow state transitions are durable and auditable.

### Evidence Intake And Storage

- Evidence can be referenced, uploaded, or linked through a controlled ingestion path.
- Evidence metadata is queryable by tenant and workflow.
- Evidence retention, integrity, and access rules are enforceable.

### Receipt Ingestion And Query

- Kernel-aligned receipts can be ingested without mutating their canonical semantics.
- Receipt ingestion validates against pinned kernel contracts.
- Receipts are queryable by tenant, intent, workflow, and time range.

### Audit And Export

- Core lifecycle events are available through audit and export interfaces.
- Exported records preserve enough provenance for external review.

### Operational Readiness

- Structured logs, metrics, and health checks exist.
- Failure modes for external dependencies are visible and recoverable.
- Contract compatibility with the pinned kernel artifact set is tested in CI.

### Security And Signing Guardrails

- Key material is not embedded in application code or repository assets.
- Signing workflows, if present in release 1, use managed key infrastructure abstractions.
- Revocation and quarantine paths exist for invalid or suspicious artifacts.

## Explicit First Release Deferrals

The following are intentionally out of scope for the first release unless later promoted with updated acceptance criteria:

- Broad end-user UI and complex workflow builders
- Full Capability Escrow execution lifecycle
- Rich adapter marketplace management
- Advanced PCCB packaging beyond a minimal orchestrated path
- Multi-region active-active deployment
- Extensive analytics or reporting surfaces beyond audit and export essentials
