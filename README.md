# Actenon Cloud

> The optional managed control plane. Multi-tenant, hosted, with evidence bundles and operator tooling. Cloud is optional — Permit, Kernel, and Scan all run without it.

## What this is

Cloud is the **managed** version of the Actenon spine. It adds:

- **Multi-tenant isolation** (Postgres RLS + Python-level checks)
- **Hosted AEI lifecycle** (create, approve, execute, evidence — 13 REST endpoints)
- **Encrypted credential store** (AES-256-GCM, per-tenant derived keys, rotation, revocation, audit)
- **Durable execution workers** (retry, dead-letter, reconciliation, cancellation)
- **Evidence bundles** (9 independent layers, each with SHA-256 hash, independently verifiable)
- **Outcome honesty** (submission is NOT execution; never green without verified receipt)
- **Insurer-facing clarity** (3 separate questions: execution integrity, authority-process integrity, business correctness)

Cloud does NOT define proof validity. The Kernel remains the verifier authority.

## What Cloud is NOT

- NOT required for local development (use `Actenon.local()`)
- NOT required for Scan (Scan has zero dependencies)
- NOT required for the Boundary Kit (middleware runs in-process)
- NOT production-ready out of the box (see Production Integration Guide)

## API surface

```
POST   /api/v1/intents                      create intent (idempotent)
GET    /api/v1/intents                      list intents (tenant-scoped)
GET    /api/v1/intents/{id}                 retrieve intent
POST   /api/v1/intents/{id}/approve         approve (requires intent.approve)
POST   /api/v1/intents/{id}/deny            deny (requires intent.approve)
POST   /api/v1/intents/{id}/execute         execute brokered (via PermitGatewayBridge)
POST   /api/v1/intents/{id}/submit          submit resource-owned
GET    /api/v1/intents/{id}/evidence        evidence bundle (9 layers)
POST   /api/v1/intents/{id}/evidence/verify verify bundle independently
GET    /api/v1/intents/{id}/outcome         honest outcome state
POST   /api/v1/credentials                  register credential (credential.manage)
GET    /api/v1/credentials                  list (redacted, credential.view)
DELETE /api/v1/credentials/{ref}            delete (credential.manage)
```

## Security architecture

| Layer | Implementation |
|---|---|
| **Credential encryption** | AES-256-GCM, per-tenant derived keys, rotation, revocation, access audit |
| **Tenant isolation** | Postgres RLS (ENABLE + FORCE) + Python-level checks |
| **Signing** | Ed25519 pilot (real asymmetric); KMS/HSM interface ready (deployment wires provider) |
| **Auth** | Bearer token + tenant-scoped permissions (intent.approve, intent.execute, credential.manage, etc.) |
| **Replay protection** | In-memory + SQLite replay stores; single-use proofs |
| **Evidence** | 9 independent layers, SHA-256 hashes, independent verification endpoint |

## Readiness (truthful)

| Component | Status |
|---|---|
| Credential encryption + isolation | ✅ Production-ready |
| Tenant isolation (RLS) | ✅ Production-ready |
| Execution workers (durable, retry, dead-letter) | ✅ Production-ready |
| Evidence bundles (9 layers) | ✅ Production-ready |
| Ed25519 signing | ✅ Pilot-ready (key on disk, not KMS) |
| KMS/HSM signing | ❌ Stub (interface exists, deployment wires provider) |
| OIDC authentication | ❌ Stub (bearer token works, no external IdP) |
| S3/GCS evidence storage | ❌ Stub (local filesystem) |
| Multi-region | ❌ N/A (infrastructure concern) |

See `readiness.yaml` for the single source of truth.
See `PRODUCTION_INTEGRATION.md` for exactly what to wire.

## Evidence bundle

9 independent artefact layers, each with its own SHA-256 hash:

1. Intent record
2. Permit authority decision
3. Approval evidence
4. Grant + reservation
5. ExecutionProof (PCCB)
6. Kernel receipt / refusal
7. Provider result
8. Resource-owned receipt (where applicable)
9. Cloud correlation record

Cloud does NOT replace Kernel or Permit artefacts with a summary blob. Each artefact is preserved independently. The bundle can be verified without trusting the Cloud UI.

## Insurer clarity

Three separate questions, honestly answered:

1. **Execution integrity** — did the action execute exactly as authorised? ✅ Yes, cryptography proves this.
2. **Authority-process integrity** — was the correct policy/approval/proof process followed? ✅ Yes, the evidence bundle proves this.
3. **Business decision correctness** — was the action the right thing to do? ❌ No. Cryptography does not prove business correctness.

See `INSURER_CLARITY.md`.

## What's in this repo

| Component | Location |
|---|---|
| FastAPI app | `app/main.py` |
| AEI API (13 endpoints) | `app/api/intents.py` |
| Encrypted credential store | `app/services/credential_store.py` |
| Execution workers | `app/services/execution_worker.py` |
| Evidence bundle service | `app/services/evidence_bundle.py` |
| PermitGatewayBridge | `app/services/permit_gateway_bridge.py` |
| Resource-owned execution | `app/services/resource_owned_execution.py` |
| RLS migrations | `migrations/versions/` |
| Readiness truth | `readiness.yaml` |
| Production integration guide | `PRODUCTION_INTEGRATION.md` |
| Insurer clarity | `INSURER_CLARITY.md` |

## Independence

Cloud depends on `actenon-kernel` + `actenon-permit` (runtime). It is NOT required by any other repo.

## License

Apache-2.0
