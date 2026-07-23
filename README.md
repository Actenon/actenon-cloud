# Actenon Cloud

> The optional managed control plane for proof-bound consequential execution. Multi-tenant, hosted, with 9-layer evidence bundles, durable execution workers, and insurer-facing clarity. **Cloud is optional** — Permit, Kernel, and Scan all run without it.

[![License: Source-available](https://img.shields.io/badge/License-source--available-red.svg)](LICENSE)
[![Visibility: Private](https://img.shields.io/badge/Repo-private-2ea44f.svg)](#what-cloud-is-not)
[![Python 3.9–3.12](https://img.shields.io/badge/Python-3.9%E2%80%933.12-blue.svg)](https://www.python.org/)
[![API: REST v1](https://img.shields.io/badge/API-REST%20v1-13%20endpoints-blue.svg)](#api-surface--13-endpoints)
[![Evidence: 9 layers](https://img.shields.io/badge/Evidence-9%20layers-orange.svg)](#the-9-layer-evidence-bundle)
[![Crypto: AES-256-GCM + Ed25519](https://img.shields.io/badge/Crypto-AES--256--GCM%20%2B%20Ed25519-red.svg)](#security-architecture)
[![Optional layer](https://img.shields.io/badge/Deployment-optional-2ea44f.svg)](#what-cloud-is-not)

---

## The Actenon ecosystem

Cloud is one of five independent repositories that together close the **execution gap** — the gap between *upstream authorization* and the *execution edge* that actually performs a consequential side effect.

| Repo | Role | Depends on |
|---|---|---|
| **`actenon-protocol`** | The neutral wire contract — what every artefact looks like on the wire | *nothing* |
| **`actenon-kernel`** | The open verifier — defines what a valid proof is | `actenon-protocol` |
| **`actenon-permit`** | The developer on-ramp + authority broker — issues grants, runs the PDP, brokers credentials | `actenon-kernel`, `actenon-protocol` |
| **`actenon-cloud`** ← you are here | The optional managed control plane — multi-tenant, hosted, evidence bundles | `actenon-kernel`, `actenon-permit` |
| **`actenon-scan`** | The independent static-analysis scanner — finds the execution gap in any codebase | *nothing* |

Cloud is the **only optional** repo. Everything else runs without it. Cloud exists for teams that want a hosted, multi-tenant control plane with durable execution workers, encrypted credential storage, and structured evidence bundles — without giving up the Kernel's verifier authority or the Protocol's wire contract.

---

## What this is

Cloud is the **managed** version of the Actenon spine. It adds:

- **Multi-tenant isolation** — Postgres Row-Level Security (`ENABLE` + `FORCE`) plus Python-level tenant checks on every query. A tenant cannot read or write another tenant's data even if the application layer has a bug.
- **Hosted AEI lifecycle** — 13 REST endpoints covering create / approve / deny / execute / submit / evidence / verify / outcome. Same lifecycle as Permit's 14-state machine, but durable and cross-process.
- **Encrypted credential store** — AES-256-GCM with per-tenant derived keys, rotation, revocation, and access audit. The master key is supplied by deployment (Vault / KMS / Secrets Manager); Cloud never persists it.
- **Durable execution workers** — retry with exponential backoff, dead-letter queue, reconciliation, and cancellation. Workers survive process restarts; in-flight executions are recoverable.
- **9-layer evidence bundles** — nine independent artefacts, each with its own SHA-256 hash, independently verifiable through a dedicated endpoint. Cloud does NOT collapse them into a summary blob.
- **Outcome honesty** — submission is NOT execution. A `submitted` state is non-final. `succeeded` requires a cryptographically verified receipt. No green checkmark without verified proof.
- **Insurer-facing clarity** — three separate questions (execution integrity, authority-process integrity, business decision correctness), each honestly answered.

Cloud does **NOT** define proof validity. The Kernel remains the verifier authority. Cloud exports Kernel-shaped artefacts (real PCCBs, real Receipts, real Refusals) for external verification — its internal storage models are not public wire contracts.

## What Cloud is NOT

- **NOT required for local development** — use `Actenon.local()` from Permit.
- **NOT required for Scan** — Scan has zero dependencies.
- **NOT required for the Boundary Kit** — middleware runs in-process at the resource boundary.
- **NOT required for Kernel verification** — the Kernel is a zero-network-call library.
- **NOT production-ready out of the box** — see [`PRODUCTION_INTEGRATION.md`](docs/PRODUCTION_INTEGRATION.md) for exactly what to wire (KMS/HSM signing, Vault/KMS master key, OIDC IdP, S3/GCS evidence storage).

If your team can run Postgres and wire three secrets, you can run Cloud. If you cannot, you can still ship a protected agent with Permit alone.

## API surface — 13 endpoints

```
POST   /api/v1/intents                       create intent (idempotent)
GET    /api/v1/intents                       list intents (tenant-scoped)
GET    /api/v1/intents/{id}                  retrieve intent
POST   /api/v1/intents/{id}/approve          approve (requires intent.approve)
POST   /api/v1/intents/{id}/deny             deny    (requires intent.approve)
POST   /api/v1/intents/{id}/execute          execute brokered (via PermitGatewayBridge)
POST   /api/v1/intents/{id}/submit           submit resource-owned
GET    /api/v1/intents/{id}/evidence         evidence bundle (9 layers)
POST   /api/v1/intents/{id}/evidence/verify  verify bundle independently
GET    /api/v1/intents/{id}/outcome          honest outcome state
POST   /api/v1/credentials                   register credential (credential.manage)
GET    /api/v1/credentials                   list (redacted, credential.view)
DELETE /api/v1/credentials/{ref}             delete (credential.manage)
```

Every endpoint is tenant-scoped. Permissions are explicit (`intent.approve`, `intent.execute`, `credential.manage`, `credential.view`, etc.) and enforced both at the API layer and inside the database (RLS).

## Security architecture

| Layer | Implementation |
|---|---|
| **Credential encryption** | AES-256-GCM, per-tenant derived keys (HKDF from master key + tenant ID), rotation, revocation, access audit. The master key is supplied by deployment — Cloud never persists it. |
| **Tenant isolation** | Postgres RLS (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY; ALTER TABLE ... FORCE ROW LEVEL SECURITY`) plus Python-level tenant checks on every query. Defense in depth — either layer alone would catch a cross-tenant leak. |
| **Signing** | Ed25519 pilot (real asymmetric, key on disk). KMS/HSM interface ready — deployment wires the provider (AWS KMS, GCP KMS, Azure Key Vault, PKCS#11 HSM). |
| **Auth** | Bearer token + tenant-scoped permissions. OIDC interface exists; bearer-token works out of the box. |
| **Replay protection** | In-memory + SQLite replay stores for dev; Postgres for production. Single-use proofs enforced by atomic transactional claim against a unique `replay_key`. |
| **Evidence** | 9 independent layers, each with its own SHA-256 hash, independently verifiable through `POST /api/v1/intents/{id}/evidence/verify`. |
| **Audit** | Hash-chained ledger of every state transition. Tamper-evident — any modification breaks the chain. |

See [`PRODUCTION_INTEGRATION.md`](docs/PRODUCTION_INTEGRATION.md) for the exact wiring path for each layer.

## The 9-layer evidence bundle

Every consequential action that runs through Cloud produces nine independent artefacts, each preserved with its own SHA-256 hash:

| # | Layer | Source | What it proves |
|---|---|---|---|
| 1 | **Intent record** | Cloud | What was requested, by whom, when. |
| 2 | **Permit authority decision** | Permit PDP | ALLOW / DENY / REQUIRE_APPROVAL with structured reason code. |
| 3 | **Approval evidence** | Cloud (if approval was required) | Who approved, when, with what permission. |
| 4 | **Grant + reservation** | Permit | The signed Grant's scopes/budget/rate/expiry, and the atomic reservation that locked the budget. |
| 5 | **ExecutionProof (PCCB)** | Kernel minter | The proof that was bound to the exact action. |
| 6 | **Kernel receipt / refusal** | Kernel verifier | Whether the proof verified at the edge, with the specific verification code on failure. |
| 7 | **Provider result** | Adapter | The provider's observed response (or `outcome_unknown` if the call did not complete). |
| 8 | **Resource-owned receipt** | Resource (in resource-owned mode) | The receipt issued by the resource boundary, where applicable. |
| 9 | **Cloud correlation record** | Cloud | How all of the above fit together in this execution. |

Cloud does NOT replace any of these with a summary blob. Each artefact is preserved independently. The bundle can be verified without trusting the Cloud UI — `POST /api/v1/intents/{id}/evidence/verify` recomputes every hash and checks every signature against the configured issuer keys.

## Outcome honesty

Cloud refuses to green-light an action unless a cryptographically verified Receipt exists. This is the **submission is not execution** rule, enforced at the data model:

| State | Meaning | Final? |
|---|---|---|
| `submitted` | The caller told Cloud the action was submitted to the resource. Cloud has NOT verified execution. | No |
| `accepted` | The resource acknowledged the submission. Still no proof of execution. | No |
| `succeeded` | A cryptographically verified Receipt exists for this action. | Yes |
| `failed` | A Receipt exists with `state=failed` (provider returned an error). | Yes |
| `refused` | A Refusal exists. The action did not execute. | Yes |
| `outcome_unknown` | The provider call did not complete (timeout, network partition). Honest about not knowing. | Yes (with caveat) |

There is no "assumed success" state. If Cloud cannot prove execution, it says so. See [`INSURER_CLARITY.md`](docs/INSURER_CLARITY.md).

## Insurer-facing clarity — three separate questions

Cryptography can prove two of these three questions. It cannot prove the third. Cloud is honest about which is which.

### Question 1 — Execution Integrity
**Did the action execute exactly as authorised, without mutation, replay, or bypass?**

What Cloud proves:
- The action parameters were bound to the proof cryptographically (SHA-256 action hash). Any mutation is detected at the edge.
- The proof was verified by the Kernel before the credential was released.
- The credential was never given to the agent — the broker resolved it internally and passed it only to the adapter.
- Replays are refused (single-use proof + lifecycle state machine + atomic replay claim).
- The provider's response was observed (or marked `outcome_unknown` if not).
- A Receipt was issued and cryptographically signed.

What Cloud does NOT prove:
- That the provider (GitHub, Stripe, etc.) executed the action correctly on their end. The provider's own response is the evidence; Cloud verifies that the response was observed, not that the provider's internal state is correct.

### Question 2 — Authority-Process Integrity
**Was the action authorised through the correct policy, approval, and proof-issuance process?**

What Cloud proves:
- A policy decision was made with a structured reason code.
- If approval was required, the approval was recorded with the approver's identity and timestamp.
- A PCCB was minted by the authority and verified at the edge.
- The Grant's scopes, budget, rate limits, and expiry were enforced.
- The entire lifecycle is recorded in the 9-layer evidence bundle with independently verifiable hashes.

What Cloud does NOT prove:
- That the policy itself was correct. If the policy says "allow all actions" and an agent deletes a production database, the authority process was followed — the policy was just bad. Cloud enforces policies; it does not write them.
- That the approver was the right person. Cloud enforces that *someone* with the permission approved; it does not verify that the permission assignment was correct.

### Question 3 — Business Decision Correctness
**Was the action the right thing to do for the business?**

What Cloud does NOT prove:
- That the action was wise, profitable, ethical, or free from fraud.
- That the parameters (refund amount, issue title, role assignment) were the correct business decision.
- That the person who requested the action was not themselves deceived, coerced, or acting maliciously within their authorised scope.

**Cryptography does not prove business correctness.** It proves that the execution and authority processes were followed. A fraudulent actor with valid credentials and correct permissions can execute a "correct" (technically valid) action that is "wrong" (business-harmful). Cloud's value is that it makes the action traceable, replayable, and auditable — so the fraud can be detected after the fact — but it cannot prevent it. See [`INSURER_CLARITY.md`](docs/INSURER_CLARITY.md) and [`docs/INSURER_PITCH.md`](https://github.com/Actenon/actenon-permit/blob/main/docs/INSURER_PITCH.md).

## Readiness (truthful)

Cloud's readiness is tracked in a single source of truth: [`readiness.yaml`](readiness.yaml). Nothing in the README or any other doc overrides it.

| Component | Status |
|---|---|
| Credential encryption + isolation | ✅ Production-ready |
| Tenant isolation (RLS) | ✅ Production-ready |
| Execution workers (durable, retry, dead-letter) | ✅ Production-ready |
| Evidence bundles (9 layers) | ✅ Production-ready |
| Outcome honesty (submission ≠ execution) | ✅ Production-ready |
| Ed25519 signing | ✅ Pilot-ready (key on disk, not KMS) |
| KMS/HSM signing | ❌ Stub (interface exists, deployment wires provider) |
| OIDC authentication | ❌ Stub (bearer token works, no external IdP) |
| S3/GCS evidence storage | ❌ Stub (local filesystem) |
| Multi-region | ❌ N/A (infrastructure concern) |

See [`PRODUCTION_INTEGRATION.md`](docs/PRODUCTION_INTEGRATION.md) for exactly what to wire to move from pilot-ready to production-ready.

## What's in this repo

| Component | Location |
|---|---|
| FastAPI app | [`app/main.py`](app/main.py) |
| AEI API (13 endpoints) | [`app/api/intents.py`](app/api/intents.py) |
| Encrypted credential store | [`app/services/credential_store.py`](app/services/credential_store.py) |
| Execution workers (durable, retry, dead-letter) | [`app/services/execution_worker.py`](app/services/execution_worker.py) |
| Evidence bundle service (9 layers) | [`app/services/evidence_bundle.py`](app/services/evidence_bundle.py) |
| PermitGatewayBridge | [`app/services/permit_gateway_bridge.py`](app/services/permit_gateway_bridge.py) |
| Resource-owned execution | [`app/services/resource_owned_execution.py`](app/services/resource_owned_execution.py) |
| RLS migrations | [`migrations/versions/`](migrations/versions/) |
| Readiness truth | [`readiness.yaml`](readiness.yaml) |
| Production integration guide | [`PRODUCTION_INTEGRATION.md`](docs/PRODUCTION_INTEGRATION.md) |
| Insurer clarity | [`INSURER_CLARITY.md`](docs/INSURER_CLARITY.md) |
| Architecture | [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Deployment topology | [`DEPLOYMENT_TOPOLOGY.md`](docs/DEPLOYMENT_TOPOLOGY.md) |
| Containerization plan | [`CONTAINERIZATION_PLAN.md`](docs/CONTAINERIZATION_PLAN.md) |
| Customer handoff guide | [`CUSTOMER_HANDOFF_GUIDE.md`](docs/CUSTOMER_HANDOFF_GUIDE.md) |
| Customer incident flow | [`CUSTOMER_INCIDENT_FLOW.md`](docs/CUSTOMER_INCIDENT_FLOW.md) |
| Exception handling runbook | [`EXCEPTION_HANDLING_RUNBOOK.md`](docs/EXCEPTION_HANDLING_RUNBOOK.md) |
| Incident triage runbook | [`INCIDENT_TRIAGE_RUNBOOK.md`](docs/INCIDENT_TRIAGE_RUNBOOK.md) |

## Independence

Cloud depends on [`actenon-kernel`](https://github.com/Actenon/actenon-kernel) + [`actenon-permit`](https://github.com/Actenon/actenon-permit) (runtime). It is **NOT** required by any other repo. The Kernel does not depend on Cloud — the normative direction is one-way: Cloud may depend on the Kernel; the Kernel must never depend on Cloud. Cloud's internal storage models (e.g. `IssuedProof`) are not public wire contracts; Cloud must export real Kernel-compatible PCCBs and sign the exact bytes produced from the Kernel PCCB unsigned payload.

## License

Source-available. See [`LICENSE`](LICENSE). This repository is published for
transparency and evaluation; it does not grant a licence to use, copy, modify
or redistribute. For commercial licensing, contact legal@actenon.dev.
