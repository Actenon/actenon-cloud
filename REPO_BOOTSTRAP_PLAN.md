# Repo Bootstrap Plan

## Goal

Stand up a credible repository skeleton for Actenon Cloud that makes the control-plane versus kernel boundary explicit and gives future implementation work a single acceptance entrypoint.

## Phase 0

### Deliverables

- repository layout for `app/`, `tests/`, `scripts/`, `docs/`, `schemas/`, `migrations/`, and `examples/`
- core product and architecture documents
- explicit kernel dependency model
- bootstrap acceptance harness in `scripts/verify.sh`
- summary harness in `scripts/judge.sh`

### Exit Criteria

- the repository passes `bash scripts/verify.sh`
- the repository passes `bash scripts/judge.sh`
- the first release scope is written and intentionally narrow

## Phase 1

### Objective

Lock the dependency posture with the open execution kernel and choose the baseline implementation stack.

### Deliverables

- validated kernel artifact publication mechanism
- pinned kernel dependency strategy
- initial service language and framework choice
- initial persistence, object-store, auth, and key-management choices
- repo-owned schemas for intake and administrative APIs

### Risks

- overcommitting to a stack before the kernel contract model is known
- accidental duplication of kernel responsibilities

## Phase 2

### Objective

Implement the backend foundation for intake, tenancy, authorization, and auditability.

### Deliverables

- authenticated intake API
- tenant model and role model
- audit event model
- initial migrations
- unit, integration, and contract test scaffolding

## Phase 3

### Objective

Implement workflow policy, approval state, evidence metadata, and receipt ingestion.

### Deliverables

- policy storage and evaluation path
- approval workflow engine
- evidence metadata service and object-store abstraction
- receipt ingestion and query APIs
- contract tests against pinned kernel receipt artifacts

## Phase 4

### Objective

Introduce carefully bounded proof, signing, escrow, and revocation capabilities.

### Deliverables

- proof and PCCB orchestration interfaces
- managed signing service integration
- initial Capability Escrow workflow
- revocation and quarantine APIs

### Guardrails

- do not claim verifier ownership
- do not embed raw key material in app code
- require stronger acceptance checks for signing and revocation paths

## Phase 5

### Objective

Operational hardening and enterprise readiness.

### Deliverables

- metrics, health checks, tracing, and alerting
- export workflows and retention controls
- performance and failure-mode testing
- documented recovery and support procedures

## Not Yet Chosen

These decisions are intentionally deferred until kernel validation and implementation planning:

- implementation language
- API framework
- database and migration tool
- queue or workflow runtime
- managed key provider
- identity provider strategy

## Bootstrap Success Definition

This bootstrap is successful if future contributors can tell, by reading the repo and running the harness, what this repository owns, what belongs in the kernel, what release 1 includes, and how to keep the boundary intact.
