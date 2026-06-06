# Blockers

## Purpose

This file lists the gaps that still prevent Actenon Cloud from being honestly described as production-ready.

It also makes clear which limitations are currently tolerable for a supervised design-partner pilot and which ones remain hard blockers for a broader cloud readiness claim.

## Managed Pilot Reality

Actenon Cloud can support a controlled pilot when the following conditions are accepted:

- one dedicated environment per design partner
- one narrow invoice payment workflow
- named operator ownership
- managed PostgreSQL and mounted persistent evidence storage
- centralized log collection
- explicit acknowledgement that auth, signing, evidence storage, and observability remain early

Those conditions can support a managed pilot. They do not remove the production blockers below.

## Production Blockers

### Identity And Access

- No enterprise operator SSO or federation is implemented.
- No production workload identity implementation exists for service-to-service auth.
- The implemented auth mode is still development-signed bearer token issuance with a bootstrap admin path.

### Signing And Trust

- Managed KMS-backed or HSM-backed signing is not implemented.
- The active proof-signing path is development-local HS256 HMAC, which is not sufficient for production trust requirements.
- Key lifecycle and trust-anchor management are still pilot-stage.

### Evidence Durability

- Evidence uploads depend on a mounted filesystem path at runtime.
- There is no native object-store write path for uploaded evidence.
- The repo does not yet implement a stronger production evidence durability or storage-isolation posture.

### Capability Release

- Capability release is still simulated.
- There is no real protected-resource broker or production adapter release path in this repo.

### Observability And Operations

- The repo implements structured logs and health checks, but no metrics exporter, tracing backend, or alerting pipeline.
- Backup and restore assumptions are documented, but restore has not been turned into an exercised operational capability here.
- Incident response, dashboards, and paging posture remain early.

### Deployment And Recovery

- A repeatable single-tenant containerized path exists, but deployment is still operator-driven.
- No automated rollout, rollback, or environment provisioning workflow is implemented.
- No production HA, autoscaling, or broader disaster recovery posture is implemented in repo artifacts.

### Tenant Isolation

- No database-native row-level security is implemented.
- No documented per-tenant key-separation strategy is enforced in runtime behavior.
- Some workflow actor fields still need tighter binding to authenticated sessions.

### Kernel And Verifier Compatibility Hardening

- Kernel-facing contracts are pinned locally, not synchronized automatically from the separate open kernel repo.
- There is no automated live compatibility workflow with the separate verifier repo or verifier interface.
- Provider integrations are still early hooks and lifecycle records rather than hardened production adapters.

### Release Governance

- Package build smoke exists, but there is no signed artifact publication flow.
- No release provenance, attestation, or dependency-vulnerability gate is implemented.

## Buyer-Facing Summary Of What Is Missing

For technical buyers, the clearest current blockers are:

- production identity for humans and services
- managed signing infrastructure
- durable evidence storage beyond mounted filesystem persistence
- full observability and incident operations
- automated deployment, rollback, and recovery
- stronger hosted isolation and multi-tenant controls

## Internal Priority Signal

If the repo needs one practical reading of these blockers, it is this:

Actenon Cloud is credible as a supervised managed pilot, but not yet credible as a broad hosted cloud product claim.
