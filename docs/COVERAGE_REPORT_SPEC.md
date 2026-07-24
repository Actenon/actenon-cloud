# Coverage Report Specification

## Purpose

This document defines the attestable coverage report that Fable 5's
review identified as the monetization key:

> "Coverage measurement is the underwriting variable. Build me the
> attestable coverage report — Scan results plus receipt volume against
> declared consequential surfaces — and the trust-score layer your
> boundary doc hints at, and this becomes the first AI control I can
> actually price."
>
> — William (underwriter), Fable 5 persona review

The coverage report is the artifact that simultaneously unlocks:
- **Insurer pricing** — William needs to know what fraction of
  consequential actions route through the gate to price the premium.
- **Auditor reliance** — Katherine needs to test completeness and
  accuracy of the evidence trail.
- **CISO sign-off** — Elena needs to demonstrate that the protected
  edge is the only path.

Nobody has built this yet. It is the most strategically underweighted
artifact in the ecosystem.

## What the report measures

The coverage report answers one question:

> **What fraction of an organization's consequential actions are
> proof-bound (covered by the Actenon gate), and what fraction are
> unguarded (running without proof)?**

The report reconciles two data sources:

1. **Scan results** — `actenon-scan` finds consequential action
   call sites in the codebase (e.g., `stripe.Refund.create()`,
   `shutil.rmtree()`, `iam.attach_role_policy()`). Each finding is a
   declared consequential surface.

2. **Receipt volume** — the Actenon evidence store contains receipts
   for every proof-bound execution. Each receipt proves that a specific
   action was gated.

The coverage fraction is:

```
coverage = (receipts for gated actions) / (scan findings for the same action types)
```

An action type with scan findings but zero receipts is **unguarded** —
it's running without proof. An action type with receipts matching scan
findings is **covered**. An action type with receipts but no scan
findings is **anomaly** — the gate is executing actions the scanner
didn't find (possibly a new code path added after the last scan).

## Report structure

The coverage report is a JSON document with the following structure:

```json
{
  "report_id": "cov_2026_07_24_acme",
  "report_version": "1.0.0",
  "generated_at": "2026-07-24T14:00:00Z",
  "generated_by": "actenon-coverage-report v1.0.0",
  "tenant_id": "tenant-acme",
  "period": {
    "start": "2026-07-17T00:00:00Z",
    "end": "2026-07-24T00:00:00Z"
  },
  "scan": {
    "scan_id": "scan_2026_07_24_001",
    "scanned_at": "2026-07-24T12:00:00Z",
    "repository": "acme/payments-agent",
    "commit": "a1b2c3d",
    "total_findings": 47,
    "findings_by_action": {
      "payment.refund": 3,
      "payment.capture": 2,
      "invoice.pay": 1,
      "customer.delete": 1,
      "shutil.rmtree": 5,
      "iam.attach_role_policy": 2,
      "stripe.Refund.create": 3
    },
    "guarded_findings": 12,
    "unguarded_findings": 35
  },
  "receipts": {
    "total_receipts": 1247,
    "receipts_by_action": {
      "payment.refund": 89,
      "payment.capture": 23,
      "invoice.pay": 12,
      "customer.delete": 0,
      "shutil.rmtree": 0,
      "iam.attach_role_policy": 0,
      "stripe.Refund.create": 0
    },
    "refusals_by_action": {
      "payment.refund": 4,
      "payment.capture": 1,
      "invoice.pay": 0
    }
  },
  "coverage": {
    "overall_fraction": 0.255,
    "by_action": {
      "payment.refund": {
        "scan_findings": 3,
        "receipts": 89,
        "refusals": 4,
        "covered": true,
        "coverage_fraction": 1.0,
        "notes": "All scan findings are guarded; receipts present"
      },
      "shutil.rmtree": {
        "scan_findings": 5,
        "receipts": 0,
        "refusals": 0,
        "covered": false,
        "coverage_fraction": 0.0,
        "notes": "5 unguarded rmtree calls; NOT proof-bound"
      },
      "iam.attach_role_policy": {
        "scan_findings": 2,
        "receipts": 0,
        "refusals": 0,
        "covered": false,
        "coverage_fraction": 0.0,
        "notes": "2 unguarded IAM calls; NOT proof-bound"
      }
    }
  },
  "anomalies": [
    {
      "type": "receipts_without_scan",
      "action": "payment.refund",
      "detail": "89 receipts for payment.refund but only 3 scan findings; possible new code path added after scan",
      "severity": "info"
    }
  ],
  "attestation": {
    "report_hash": "sha256:abc123...",
    "signed_by": "actenon-coverage-report",
    "key_id": "issuer:coverage:2026-07",
    "signature": "base64url:...",
    "signature_algorithm": "EdDSA"
  }
}
```

## Field definitions

### `scan` section

| Field | Type | Description |
|---|---|---|
| `scan_id` | string | Unique identifier for the scan run |
| `scanned_at` | ISO 8601 | When the scan was run |
| `repository` | string | The repository URL that was scanned |
| `commit` | string | The git commit hash that was scanned |
| `total_findings` | int | Total number of consequential action call sites found |
| `findings_by_action` | map | Action type → count of call sites |
| `guarded_findings` | int | Findings where a guard call appears lexically before the sink |
| `unguarded_findings` | int | Findings with no guard call (the execution gap) |

### `receipts` section

| Field | Type | Description |
|---|---|---|
| `total_receipts` | int | Total receipts in the evidence store for the period |
| `receipts_by_action` | map | Action type → count of receipts |
| `refusals_by_action` | map | Action type → count of refusals (proofs that were rejected) |

### `coverage` section

| Field | Type | Description |
|---|---|---|
| `overall_fraction` | float | Fraction of consequential actions that are proof-bound (0.0–1.0) |
| `by_action` | map | Per-action coverage detail |
| `by_action.*.covered` | bool | True if the action has both scan findings and receipts |
| `by_action.*.coverage_fraction` | float | receipts / max(scan_findings, 1) |
| `by_action.*.notes` | string | Human-readable explanation |

### `anomalies` section

Anomalies are conditions that warrant investigation:

| Type | Meaning |
|---|---|
| `receipts_without_scan` | Receipts exist for an action the scanner didn't find — new code path? |
| `scan_without_receipts` | Scan findings exist but no receipts — unguarded actions are running |
| `refusal_spike` | Refusal rate > 5% for an action — possible authority issue or idempotency bug |
| `replay_detected` | Any `REPLAY_DETECTED` refusal — potential replay attack or idempotency bug |

### `attestation` section

The report is cryptographically attested so a third party (insurer,
auditor, regulator) can verify it was produced by the coverage report
tool and has not been tampered with:

| Field | Type | Description |
|---|---|---|
| `report_hash` | string | SHA-256 hash of the report (excluding the attestation section) |
| `signed_by` | string | Identifier of the signing entity |
| `key_id` | string | The key ID used to sign (resolvable via well-known key discovery) |
| `signature` | string | Ed25519 signature over the report hash, base64url-encoded |
| `signature_algorithm` | string | Always "EdDSA" for v1 |

## How the report is generated

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  actenon-   │     │  evidence    │     │  coverage report │
│  scan       │     │  store       │     │  generator       │
│             │     │              │     │                  │
│  scan repo  │────▶│              │     │                  │
│  find sinks │     │  receipts    │     │                  │
│             │     │  refusals    │     │                  │
│             │     │     │        │     │                  │
│             │     │     └───────▶│────▶│  reconcile       │
│             │     │              │     │  sign            │
│             │─────────────────────────▶│  output          │
└─────────────┘     └──────────────┘     └────────┬─────────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │  coverage     │
                                          │  report.json  │
                                          │  (attested)   │
                                          └───────────────┘
```

1. **Scan** runs `actenon-scan` against the repository at a specific commit.
2. **Query** queries the evidence store for receipts and refusals in the period.
3. **Reconcile** matches scan findings to receipts by action type.
4. **Sign** signs the report hash with the coverage report key.
5. **Output** writes the attested JSON report.

## How the report is verified

A third party (insurer, auditor) verifies the report as follows:

```bash
# 1. Verify the report signature
actenon-kernel verify-coverage-report --report coverage-report.json

# 2. Verify the scan results independently (re-run scan against the same commit)
actenon-scan scan --commit a1b2c3d --output /tmp/independent-scan.json

# 3. Verify the receipt volume independently (query the evidence store)
actenon-kernel evidence query --period 2026-07-17:2026-07-24 --output /tmp/independent-receipts.json

# 4. Compare the independent results to the report
actenon-coverage-report verify --report coverage-report.json \
  --scan /tmp/independent-scan.json \
  --receipts /tmp/independent-receipts.json
```

If all three checks pass, the third party can rely on the report's
coverage fraction for their own purposes (pricing a premium, testing
completeness, signing off on a control).

## What the report does NOT claim

Following the `INSURER_CLARITY.md` doctrine, the coverage report does
NOT claim:

- **That the unguarded actions are dangerous.** Scan findings show
  where consequential actions are reachable; they don't prove the
  action is dangerous in context. The report shows coverage, not risk.
- **That the guarded actions were the right actions to take.** The
  report proves the action was proof-bound and executed; it does not
  prove the business decision was correct (that's the third question
  in the `INSURER_CLARITY.md` framework — cryptography cannot prove
  business correctness).
- **That the coverage fraction is sufficient.** The report shows the
  fraction; the insurer/auditor/CISO decides what fraction is
  acceptable for their risk appetite.

## Implementation status

This is a **specification**, not a working implementation. The
implementation will be built in a follow-up PR and will live in
`actenon-kernel/scripts/coverage_report.py` (generator) and
`actenon-kernel/actenon/coverage/` (library code).

The implementation depends on:
- `actenon-scan` being able to output structured JSON (already supported
  via `--format json`)
- The evidence store having a query API (already supported via
  `actenon-kernel evidence query`)
- A coverage report signing key (needs KMS custody, per the key-lifecycle
  state machine)

## See also

- [INSURER_CLARITY.md](INSURER_CLARITY.md) — the three-questions doctrine
  that governs what the report does and does not claim
- [COMPLIANCE_MAPPING.md](COMPLIANCE_MAPPING.md) — how the report maps
  to OWASP LLM/Agentic and NIST AI RMF
- [CONTROL_PLANE_RELEASE_READINESS.md](CONTROL_PLANE_RELEASE_READINESS.md) —
  the coverage report is listed as a future commercial feature

---

*This spec is the artifact Fable 5's review offered to "shortcut real
adoption conversations." The coverage report is the single artifact that
simultaneously unlocks insurer pricing, auditor reliance, and CISO
sign-off. Nobody has built it yet; this spec is the first step.*
