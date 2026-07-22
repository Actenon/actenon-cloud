# Request Lifecycle

## Purpose

This document explains how an Action Intent moves through Actenon Cloud from intake to terminal governance outcomes.

## Important Boundary

The lifecycle below is a control-plane lifecycle. It describes intake, approvals, observation, indexing, proof packaging, and governance actions. It does not replace the execution lifecycle of the open kernel.

## Lifecycle Phases

### 1. Submission And Admission

The client submits a control-plane intake envelope that includes:

- tenant context
- requester identity context
- idempotency key
- canonical kernel Action Intent payload or reference
- optional policy binding hints
- optional finance routing metadata for indexing

The control plane validates tenant context, checks the pinned kernel contract reference, stores the canonical payload immutably, creates an `ActionIntentRecord`, and sets initial state:

- `intake_state=RECEIVED`
- `approval_state=NOT_STARTED`
- `proof_state=NOT_REQUESTED`
- `execution_state=NOT_REQUESTED`
- `receipt_state=NONE`

### 2. Policy Resolution

The intake layer selects the applicable tenant policy pack and evaluates workflow rules against:

- finance action class
- derived finance indexes
- requester role and membership
- submission channel
- evidence prerequisites

If the request is invalid or disallowed, the control plane moves to a terminal intake or approval rejection state without invoking downstream execution.

### 3. Approval Orchestration

The approval engine creates one or more `ApprovalRequest` records. Approvers submit `ApprovalDecision` records that are immutable once written.

Possible approval outcomes:

- no approval required
- approval satisfied
- rejected
- expired
- canceled

The approval state axis changes independently of proof, execution, and receipt state.

### 4. Proof Issuance And Escrow Hold Readiness

After approvals and required evidence are satisfied, the Action Intent becomes eligible for bounded proof issuance and, if needed, escrow hold creation.

This is still the boundary between governance and execution:

- the control plane may issue a bounded proof
- the control plane may create an escrow hold that copies the proof's exact audience, scope, and action digest
- the control plane may later release a minimal capability from that hold
- the kernel remains the execution authority

At this point the control plane keeps `execution_state=NOT_REQUESTED` until an escrow hold or execution handoff actually occurs.

### 5. External Execution Observation

The control plane observes acknowledgments, provider callbacks, or kernel-side status artifacts. It records these observations through escrow execution updates, `ProviderExecutionHook`, or receipt-related references.

Execution state values are intentionally coarse:

- `NOT_REQUESTED`
- `CAPABILITY_HELD`
- `CAPABILITY_RELEASED`
- `DISPATCH_REQUESTED`
- `DISPATCH_CONFIRMED`
- `RESULT_OBSERVED`
- `FAILURE_OBSERVED`
- `REVOKED`
- `QUARANTINED`
- `EXPIRED`

These are observation states only and must not be treated as a replacement for kernel execution semantics.

### 6. Receipt Ingestion And Indexing

Once a kernel-aligned receipt is available, the control plane ingests it as an immutable `ReceiptRecord`, validates it against the pinned kernel contract, computes derived query indexes, and updates:

- `receipt_state=RECEIVED`
- then `receipt_state=INDEXED`
- then `receipt_state=RECONCILED` when downstream checks complete

### 7. Proof Or PCCB Issuance

If policy, evidence, approvals, and observed receipts satisfy issuance rules, the control plane may create an `IssuedProof` or PCCB package. This step may use `SigningKeyReference` metadata to request a managed signing operation.

The proof state axis should progress independently:

- `NOT_REQUESTED`
- `ELIGIBLE`
- `ISSUANCE_REQUESTED`
- `ISSUED`
- `FAILED`
- `REVOKED`

### 8. Reconciliation, Export, And Governance Control

The reconciliation layer checks that expected business outcomes and observed artifacts line up. The audit layer records each important state change.

If a proof, receipt, evidence object, or escrow record becomes suspicious or invalid, the control plane may apply:

- quarantine
- release from quarantine
- revocation

These actions are captured in `ArtifactControlState` and linked audit records rather than by mutating canonical artifacts.

## State Transition Summary

| Phase | Primary Records | Main State Axes Touched |
| --- | --- | --- |
| Submission | ActionIntentRecord, AuditEvent | `intake_state` |
| Policy resolution | PolicyPack, WorkflowRule, ActionIntentRecord | `intake_state`, `approval_state` |
| Approvals | ApprovalRequest, ApprovalDecision | `approval_state` |
| Proof and escrow readiness | ActionIntentRecord, IssuedProof, EscrowRecord | `proof_state`, `execution_state` |
| Dispatch readiness | ActionIntentRecord, EscrowRecord, ProviderExecutionHook | `execution_state` |
| Execution observation | EscrowRecord, ProviderExecutionHook, ActionIntentRecord | `execution_state` |
| Receipt ingestion | ReceiptRecord, ReplayConsumptionState | `receipt_state` |
| Proof issuance | IssuedProof, SigningKeyReference | `proof_state` |
| Reconciliation and controls | ReconciliationRecord, ArtifactControlState, AuditEvent | `receipt_state`, `artifact_control_state`, `proof_state` |

## Terminal Outcomes

An Action Intent eventually reaches one of the following control-plane outcomes:

- rejected before execution
- approved and awaiting external execution result
- completed with observed receipt and optional proof issuance
- completed with receipt mismatch requiring manual review
- quarantined or revoked due to post-fact review or invalidation

## Release 1 Narrowing

Release 1 should fully support:

- submission and admission
- finance approval orchestration
- evidence linkage
- bounded proof issuance with development-local signing
- narrow capability escrow with development-local simulated release
- coarse execution observation
- receipt ingestion and indexing
- audit and reconciliation

Receipt-bound proof issuance, external managed capability release, managed-key integrations, and advanced provider-hook automation should stay narrow and interface-driven until later passes.
