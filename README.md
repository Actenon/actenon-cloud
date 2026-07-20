# Actenon Cloud

Actenon Cloud is the managed control plane for governed agent execution. It is
**not the execution kernel or verifier** — that role belongs to the open
[actenon-kernel](https://github.com/Actenon/actenon-kernel) repo. Actenon Cloud
provides the operational layer around the open proof gate and receipt standard,
including policy management, approvals, tenant administration, audit storage,
dashboards, and hosted evidence workflows.

## What Actenon Cloud Does

Actenon Cloud implements the **control-plane scope** for governed agent
execution: it receives action intents, evaluates policy, issues proofs (via
the kernel spine), records evidence and receipts, manages approvals, and
provides the operator UI for finance reviewers and administrators. It does
not verify proofs at the execution edge — that is the kernel's job.

## What The Invoice Payment Pilot Covers

The **narrow pilot scope** is invoice payment execution governance: a finance
reviewer approves or blocks a refund action intent, the control plane issues
a proof, and a receipt is recorded. The pilot covers one action type
(`payment.refund`) against one mock payment provider. It does not cover
general-purpose agent workflows, multi-cloud deployment, or production
capability release.

## Deployment Shape

The **managed deployment posture** is a single-tenant container deployment:
one dedicated runtime, one managed PostgreSQL instance, one mounted evidence
volume, behind a TLS-terminating reverse proxy. The customer does not run
the control plane — the provider operates it. See `docker-compose.yml` and
`HOSTED_PILOT_TOPOLOGY.md` for the concrete shape.

## Provider And Customer Ownership

The **provider** (Actenon) operates the control plane, database, evidence
storage, and signing infrastructure. The **customer** provides the action
intents, the approval workflow (finance reviewers), and the payment provider
credentials (via the broker, never visible to the agent). The customer owns
their data; the provider owns the runtime.

## Kernel And Verifier Boundary

Actenon Cloud depends on the **open kernel** (`actenon-kernel`) for the PCCB
builder, the verifier, and the canonicalization profile. The kernel is the
source of truth for the proof artifact. Actenon Cloud calls kernel code to
build and sign PCCBs — it does not maintain a parallel proof format. The
kernel is open and independently auditable at
[github.com/Actenon/actenon-kernel](https://github.com/Actenon/actenon-kernel).

## What Is Still Early

The current production limits are honestly documented in `BLOCKERS.md` and
`SHIP_STATUS.md`. Key limitations:
- Proof signing uses Ed25519 (dev-HMAC has been removed). Production boot
  is refused without `ACTENON_KMS_ENDPOINT`; a real KMS backend must be
  provisioned by the operator.
- Capability release is real — the broker issues signed JWT-like capability
  tokens via the permit-broker path. A real production adapter release path
  requires operator-provisioned provider credentials.
- OIDC is implemented but not yet tested end-to-end with a real OIDC issuer
  (dev bearer is refused in production). Tenant isolation (Postgres RLS)
  requires a managed PostgreSQL instance. Automated deploy/rollback is not
  yet implemented.
- The repo is **not production-ready** — it is credible as a supervised
  managed pilot, but not as a broad hosted cloud product

Note: receipt counter-signing has a separate HSM/KMS custody interface that
is specified but not yet wired to a real hardware-backed signer.

No valid proof, no execution.
