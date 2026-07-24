# CISO Pilot-Approval Conditions

## Purpose

This document defines the conditions under which a CISO in a regulated
fintech (Elena, from Fable 5's persona review) can approve a bounded
pilot of the Actenon proof-bound execution edge on the refund path.

It is written as a contract between the engineering team proposing the
pilot and the CISO signing the risk acceptance. It is deliberately
specific: each condition is testable, each dependency is named, and each
sign-off requires evidence.

## Scope

**Approved for:** a bounded pilot on the `payment.refund` action path,
using the Stripe adapter in test mode against a staging Stripe account,
for a single design-partner tenant.

**Not approved for:**
- production payment movement
- any action other than `payment.refund`
- multi-tenant deployment
- brokered execution mode (resource-owned only for the pilot)
- any path where the protected edge is not the only path to the side effect

## Pilot duration

90 days from the date of CISO sign-off, renewable once on evidence of
the KMS milestone being met (see Condition 1 below). If the KMS
milestone is not met within 90 days, the pilot MUST be decommissioned.

## Conditions

### Condition 1: KMS custody (CONTINGENT — blocks production, not pilot)

The pilot MAY proceed with `pilot_local_eddsa` signing (Ed25519 with the
private key on disk behind `ACTENON_ALLOW_PILOT_LOCAL_EDDSA_IN_PRODUCTION=1`)
for the duration of the 90-day pilot. The CISO acknowledges that:

- The pilot signing key is on disk, not in KMS.
- The `ACTENON_ALLOW_PILOT_LOCAL_EDDSA_IN_PRODUCTION` flag is set once
  and MUST be unset before any production traffic routes through the gate.
- The KMS backend (AWS KMS, per `actenon/proof/signers/aws_kms.py`) is
  the gate for production promotion, not for pilot start.

**Production promotion dependency:** before any production payment
movement, ALL of the following must be true:
1. A real AWS KMS Ed25519 key is provisioned in the production AWS account.
2. The key's lifecycle state is `active` per the key-lifecycle state machine.
3. The key's public key is published via `actenon-kernel keys publish`.
4. The pilot signing key is rotated to `retired` (not `hard_revoked` —
   historical pilot receipts must remain verifiable).
5. The `ACTENON_ALLOW_PILOT_LOCAL_EDDSA_IN_PRODUCTION` flag is unset and
   the boot-refusal guard is verified to reject pilot signing.

**Evidence required for production sign-off:**
- KMS key ARN and region
- Well-known key discovery document URL
- Evidence that the rotation runbook was executed (see
  `docs/reference/ecosystem/KMS_ROTATION_RUNBOOK.md`)
- Evidence that the boot-refusal guard rejects pilot signing without the
  flag

### Condition 2: The protected edge is the only path

The refund path MUST be the only path from the agent to the Stripe
refund API. Specifically:

- The Stripe secret key MUST NOT be available to the agent process.
- The Stripe secret key MUST be registered with the Actenon credential
  broker, not passed as an environment variable to the agent.
- The agent MUST NOT have direct network access to `api.stripe.com`.
  Network policy MUST restrict Stripe API access to the Actenon
  broker process only.
- The `actenon.boundary.yaml` manifest MUST list `POST /refunds` as a
  protected boundary with `payment.refund` as the action.

**Evidence required:**
- Network policy configuration showing Stripe API access restricted to
  the broker process
- The `actenon.boundary.yaml` manifest
- A Scan report showing no unguarded `stripe.Refund.create()` calls in
  the agent codebase

### Condition 3: Observe-then-enforce rollout

The pilot MUST follow the observe-then-enforce rollout:

- **Week 1-2:** observe mode. The boundary middleware logs what would
  be refused but does not block. Daily review of the observe log.
- **Week 3:** warn mode. The middleware logs warnings but does not block.
  Daily review of warnings.
- **Week 4+:** enforce mode. The middleware blocks unproven requests.
  Pagerduty alerting on refusal spikes.

**Evidence required:**
- Observe log review notes for weeks 1-2
- Warn log review notes for week 3
- Pagerduty alert configuration for enforce mode

### Condition 4: Break-glass procedure

The pilot MUST have a documented break-glass procedure for the
authority-down scenario (Fable 5's SRE persona, Aoife). The procedure
MUST specify:

- Who can invoke the break-glass (named individuals, not roles)
- How the break-glass is bounded (time-limited, audit-logged)
- That the break-glass itself emits receipts (the exception is as
  auditable as the rule)
- The post-incident review process

**Evidence required:**
- The break-glass runbook (see `BREAK_GLASS_RUNBOOK.md`)
- The list of named individuals authorized to invoke break-glass
- The audit log configuration that records break-glass invocations

### Condition 5: Evidence retention and verifiability

The pilot MUST retain evidence for the duration of the pilot plus 90
days. Specifically:

- Every receipt and refusal MUST be persisted to the evidence store
  (LocalFsEvidenceStore for the pilot; S3 for production).
- The evidence store MUST be backed up daily.
- The receipt verification endpoint (`/evidence/verify`) MUST be
  accessible to the CISO's audit team.
- The receipt signature MUST be verifiable against the published
  well-known key discovery document.

**Evidence required:**
- Backup configuration for the evidence store
- The well-known key discovery document URL
- A sample receipt verified by the audit team

### Condition 6: Refusal rate monitoring

The pilot MUST monitor the refusal rate and alert on anomalies:

- Refusal rate > 5% of request volume in any 1-hour window → alert
- Refusal rate > 20% of request volume in any 15-minute window → page
- Any refusal with code `REPLAY_DETECTED` → immediate page (potential
  replay attack or idempotency bug)
- Any refusal with code `AUTHORITY_REVOKED` → immediate page (authority
  compromise)

**Evidence required:**
- Alerting configuration
- The first week's refusal rate dashboard

### Condition 7: Tenant isolation

The pilot MUST be single-tenant. Specifically:

- The pilot runs in a dedicated environment (separate database, separate
  evidence store, separate signing key).
- The pilot tenant ID is hardcoded in the configuration; no multi-tenant
  routing.
- The agent process runs with credentials scoped to the pilot tenant
  only.

**Evidence required:**
- Infrastructure configuration showing single-tenant isolation
- Credential scope configuration

## Sign-off

By signing below, the CISO acknowledges:

1. The conditions above are met or will be met before the pilot starts.
2. The pilot is bounded to 90 days, renewable once on KMS milestone evidence.
3. Production promotion requires explicit re-approval after KMS milestone.
4. The CISO's audit team has access to the evidence store and verification
   endpoint for the duration of the pilot.

| Role | Name | Date | Signature |
|---|---|---|---|
| CISO | | | |
| Engineering Lead | | | |
| Pilot Operator | | | |

## Post-pilot review

Within 30 days of pilot completion, the engineering team MUST produce a
post-pilot review covering:

- Refusal rate over the pilot period (by code, by action)
- Any break-glass invocations and their outcomes
- Any reconciliation mismatches detected by the Stripe adapter
- The KMS milestone status (met / not met / blocked)
- Recommendation: decommission, extend pilot, or promote to production

The CISO MUST review and sign off on the post-pilot review before any
production promotion decision.

---

*This document is the artifact Fable 5's review offered to "shortcut
real adoption conversations." It is specific enough to be a contract
and honest enough to survive an audit. The KMS contingency is the
single hardest dependency; everything else is operational discipline.*
