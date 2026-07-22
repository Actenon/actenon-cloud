# Architecture

## System Role

Actenon Cloud is the hosted control-plane service above a separate open execution kernel. The control plane manages enterprise workflow, approval, evidence, receipt access, and governance concerns. The kernel remains the execution and verifier authority.

## Architecture Goals

- Keep execution and verifier semantics in the kernel
- Provide tenant-aware APIs and durable workflow state in the control plane
- Preserve evidence and auditability across all important actions
- Keep the first release backend-first and operationally credible

## High-Level Domains

### Admission And Intake

- Accept Action Intents through authenticated APIs
- Validate tenant context and request shape
- Create durable intent records and audit events

### Policy And Workflow

- Store tenant and workflow policy versions
- Evaluate approval requirements
- Drive approval state transitions and workflow progression

### Evidence Service

- Ingest evidence metadata and references
- Enforce access control and retention hooks
- Link evidence to intents, approvals, receipts, and revocations

### Receipt Service

- Ingest kernel-aligned receipts
- Validate compatibility against pinned kernel schemas
- Support query and export surfaces

### Proof, Signing, And Key Lifecycle

- Orchestrate PCCB and proof issuance workflows above kernel outputs
- Manage signing requests through external key-management abstractions
- Record signing lineage, revocation, and quarantine status

### Capability Escrow

- Hold and release approved capabilities according to policy
- Maintain auditability around release, revocation, and quarantine events

### Adapter Orchestration Hooks

- Trigger or coordinate adapter-facing control-plane actions
- Avoid embedding kernel execution behavior in this layer

### Enterprise Administration

- Manage tenants, roles, authz, service credentials, and configuration
- Expose operator and audit surfaces

## Ownership Boundary

### Open Execution Kernel Owns

- execution semantics
- verifier and proof validation semantics
- kernel-native contracts for receipts and execution outcomes
- runtime-side adapter execution behavior

### Actenon Cloud Owns

- intake, governance, approval, and audit flows
- tenant and administrative boundaries
- evidence and customer-facing custody concerns
- query, export, revocation, and quarantine APIs
- orchestration around signing, proofs, and escrow

### Shared Surface

The shared surface is the contract boundary. The control plane depends on published kernel artifacts and must not silently redefine them.

## Recommended Service Shape

This repository should start with a modular backend application rather than many separate deployables. A pragmatic early shape is:

- one API service with clear domain modules
- one relational system of record
- one evidence storage surface, currently filesystem-backed with room for later external storage integration
- one managed key interface for signing
- one asynchronous work mechanism for long-running workflows

This is a recommended baseline, not an implemented decision.

## Release 1 Architecture Slice

Release 1 should implement only the minimum credible slice:

- intake API
- tenant and auth foundations
- workflow and approval engine
- evidence metadata path
- receipt ingestion and query path
- audit and export interfaces

The more sensitive proof, signing, escrow, and complex adapter orchestration areas should initially be represented by clean interfaces and data models, not broad production features.

## Data Responsibilities

- Relational data store for tenants, intents, policies, approvals, receipts indexes, audit events, and revocation state
- Object storage for evidence and export artifacts
- Managed key infrastructure for signing and key lifecycle

Exact technology selections remain open.

## Operational Requirements

- structured logging
- metrics and health checks
- durable audit trails
- explicit dependency failure handling
- contract compatibility checks against the kernel

## Deliberate Deferrals

- rich graphical workflow design
- broad self-service UI
- large-scale analytics
- multi-region topology design
- marketplace-grade adapter management
