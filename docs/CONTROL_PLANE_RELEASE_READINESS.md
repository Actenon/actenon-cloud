# Control Plane Release Readiness

## Basis

This assessment reflects the code, tests, and deployment artifacts present in this repo on April 9, 2026. It describes implemented behavior and current operating assumptions, not target architecture.

## Readiness Summary

| Scope | Rating | Honest claim |
| --- | --- | --- |
| Internal development readiness | Green | The repo is usable for local development, contract checks, and controlled engineering iteration. |
| Design-partner pilot readiness | Amber | The service can support a supervised single-tenant invoice payment pilot when it is deployed and operated deliberately by a named team. |
| Production deployment readiness | Red | The repo does not yet implement the identity, signing, storage, observability, recovery, and automation posture needed for a broad hosted product claim. |

## Truth By Surface

| Surface | Implemented now | Honest pilot claim | Not yet true |
| --- | --- | --- | --- |
| Deployment | Single-process FastAPI service, migrations, local SQLite path, and a repeatable containerized path using the same app image. | A managed team can run one dedicated pilot environment per design partner using the documented containerized path plus managed PostgreSQL and mounted persistent evidence storage. | No automated rollout pipeline, no exercised restore path, no HA posture, no autoscaling, and no self-serve provisioning flow. |
| Auth | OIDC token verification implemented with JWKS caching. Dev bearer path is refused in production by config guard. Bootstrap admin backdoor exists but is refused in production. | Enough access control exists for a controlled pilot with explicit operator ownership and non-default secrets. | No enterprise SSO tested end-to-end with a real OIDC issuer, no federation, no production workload identity, and no mature operator lifecycle controls. Bootstrap admin backdoor still exists (refused in production by config guard). |
| Signing | Proof issuance uses Ed25519 exclusively (dev-HMAC has been removed). Production boot is refused without `ACTENON_KMS_ENDPOINT`. Key rotation works; published JWKS-style verification key set contains all known keys. | The repo can issue pilot proofs with real asymmetric signing and record signing operations for controlled evaluation. | No real KMS backend (AWS/GCP/HSM) wired — the adapter interface and boot-refusal guard are in place but need a real KMS endpoint provisioned by the operator. |
| Evidence storage | Evidence metadata is persisted and uploads are written to a filesystem-backed path checked by readiness. Field-classification layer implemented — PHI/PII fields are replaced with salted commitments in immutable records (GDPR Art.17). | A managed pilot can use mounted persistent writable storage with explicit backup handling. | Commitment layer not yet wired into the receipt ingestion path. ObjectStoreEvidenceStore (S3) not implemented; LocalFsEvidenceStore is current. Per-tenant salts not yet generated/stored. |
| Observability | Structured application logs, request IDs, and live or ready health endpoints are implemented. `/metrics` endpoint exposes Prometheus-format metrics. OpenTelemetry tracing instrumentation added (optional, guarded by import). Alert rules shipped in `config/alerts.yml`. | Operators can monitor a pilot through health endpoints, Prometheus metrics, and centralized log collection. | OTel collector, Prometheus scrape config, and alerting pipeline must be provisioned by the operator. No exercised operational dashboards or paging flow. |
| Hosting model | The repo supports a managed single-tenant operating model with one narrow invoice payment workflow. | Suitable for supervised design-partner execution under explicit scope and operator control. | Not a broad multi-tenant SaaS control plane, not a public cloud product, and not a zero-touch hosted service. |
| Kernel and verifier boundary | Cloud issues and consumes kernel-aligned artifacts and keeps proof verification outside this repo. Contract tests pin the current Cloud to Kernel-facing PCCB expectations. | The control layer can operate against the separate kernel and separate verifier boundary without absorbing verifier responsibilities. | No automated live sync with upstream kernel publication and no live verifier-compatibility workflow. |

## Why Managed Pilot Use Is Plausible

The repo is credible for a managed pilot because the current implementation is narrow and legible:

- one invoice payment workflow is implemented end to end
- the runtime can be started, migrated, and health-checked repeatably
- policy, approvals, evidence, issuance, escrow state, receipts, and audit traces are present
- the repo now carries explicit contract tests around kernel-facing issuance and refusal behavior
- the hosting assumption is one dedicated environment under named operator ownership

That is enough for a supervised design-partner pilot. It is not enough for a broader product readiness claim.

## Why Production Cloud Readiness Is Still Red

The repo should still be described as not production-ready because the following are missing or early:

- production identity for humans and services
- managed signing infrastructure
- native durable evidence storage beyond mounted filesystem persistence
- metrics, tracing, alerting, and exercised incident operations
- automated deployment, rollback, backup validation, and disaster recovery drills
- stronger tenant isolation and broader hosted operating controls

## Minimum Entry Conditions For A Managed Pilot

Before a design-partner pilot starts, this repo should be operated with:

- non-default secrets
- a dedicated pilot environment for the design partner
- managed PostgreSQL rather than local SQLite
- mounted persistent evidence storage with explicit backup handling
- TLS ingress or reverse proxy
- centralized log collection
- named operator ownership and support coverage
- explicit acknowledgement that auth, signing, evidence storage, and observability remain pilot-stage

## What Must Change Before A Production Claim

- test OIDC integration end-to-end with a real OIDC issuer; remove the bootstrap admin backdoor
- provision a real KMS/HSM endpoint and wire it to the Ed25519 signing backend
- wire the commitment layer into receipt ingestion; implement S3-backed evidence storage with per-tenant salts
- provision OTel collector, Prometheus scrape config, and alerting pipeline
- automate deployment, rollback, and restore workflows
- deploy on managed PostgreSQL with RLS enabled; harden tenant isolation and hosting controls
- automate compatibility checking against the separate kernel and verifier boundaries
