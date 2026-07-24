# Break-Glass Runbook: Authority-Down Scenario

## Purpose

This runbook defines the break-glass procedure for the authority-down
scenario identified by Fable 5's SRE persona (Aoife):

> "The authority that mints proofs has a bad deploy, and now every
> refund, every deploy, every consequential action in the company
> refuses. That's not a bug in your model — it *is* your model — but
> it means Permit and the replay store just became tier-0 with the
> same availability requirements as payments itself."

The break-glass is the controlled exception to the fail-closed model.
It is designed so that the exception is as auditable as the rule:
every break-glass invocation emits a receipt, is time-limited, and is
reviewed post-incident.

## When to invoke

Invoke the break-glass ONLY when ALL of the following are true:

1. **The authority is down.** The proof-issuing service is unavailable
   or returning errors, preventing the minting of new proofs.
2. **The action is urgent.** A consequential action (refund, payment
   capture, etc.) MUST execute within a time window that does not allow
   for authority recovery.
3. **No valid proof exists.** There is no pre-existing proof that covers
   the exact action, target, and time window.
4. **Named operator approval.** A named operator (see the authorized
   list below) has approved the break-glass invocation.

Do NOT invoke the break-glass for:
- Routine actions that can wait for authority recovery
- Actions where a valid proof can be minted by an alternative authority
- Non-urgent actions (use the normal proof-bound path)

## Authorized operators

The following named individuals are authorized to invoke the break-glass:

| Name | Role | Contact |
|---|---|---|
| *(to be filled by the pilot operator)* | Pilot Operator | |
| *(to be filled by the engineering lead)* | Engineering Lead | |
| *(to be filled by the CISO)* | CISO | |

Break-glass authorization is personal and non-delegable. If none of the
authorized operators are available, the action MUST wait.

## Procedure

### Step 1: Confirm the authority is down

Before invoking break-glass, confirm that the authority is actually
unavailable:

```bash
# Check the authority health endpoint
curl -f https://authority.example.com/health

# If the endpoint is down, check the authority's last known status
actenon-kernel doctor --deep
```

If the authority is healthy but returning errors, investigate the
errors before invoking break-glass. The issue may be a configuration
problem, not an authority outage.

### Step 2: Document the break-glass invocation

Every break-glass invocation MUST be documented BEFORE the action
executes. The documentation is a structured record:

```json
{
  "break_glass_id": "bg_2026_07_24_001",
  "invoked_by": "ravi@example.com",
  "approved_by": "elena@example.com",
  "reason": "authority down; customer refund must execute within 1h SLA",
  "action": "payment.refund",
  "target": "pi_abc123",
  "params": {"amount": 2500, "currency": "GBP", "reason": "requested_by_customer"},
  "authority_status": "unavailable (health check failed at 2026-07-24T14:23Z)",
  "invoked_at": "2026-07-24T14:25Z",
  "expected_duration": "5 minutes"
}
```

Store this record in the break-glass log before proceeding.

### Step 3: Execute the action with break-glass proof

The break-glass path uses a special proof type that is:
- Signed by the break-glass key (a separate key from the authority key)
- Time-limited (expires after 5 minutes, not the usual 15 minutes)
- Single-use (replay protection still applies)
- Clearly marked as `break_glass=true` in the receipt

```bash
# Generate a break-glass proof
actenon-permit break-glass create \
  --action "payment.refund" \
  --target "pi_abc123" \
  --params '{"amount": 2500, "currency": "GBP", "reason": "requested_by_customer"}' \
  --approved-by "elena@example.com" \
  --reason "authority down; customer refund SLA" \
  --ttl 300 \
  --output /tmp/break-glass-proof.json

# Execute the action with the break-glass proof
actenon-permit intent execute \
  --intent /tmp/intent.json \
  --proof /tmp/break-glass-proof.json \
  --audience "service:payments"
```

The execution emits a receipt with `break_glass=true` in the metadata.
This receipt is indistinguishable from a normal receipt in structure
but is clearly marked as a break-glass invocation.

### Step 4: Verify the action executed

After the break-glass execution, verify the action landed:

```bash
# Check the receipt
actenon-kernel verify-receipt --receipt /tmp/receipt.json

# Reconcile with the provider (Stripe adapter does this automatically)
# The reconciliation confirms the provider accepted the action
```

### Step 5: Restore authority and decommission break-glass

As soon as the authority is restored:

1. Verify the authority is healthy:
   ```bash
   curl -f https://authority.example.com/health
   ```

2. Disable the break-glass key:
   ```bash
   actenon-permit break-glass disable --key-id bg_key_2026_07
   ```

3. Confirm no further break-glass invocations are possible:
   ```bash
   actenon-permit break-glass status
   # Expected: "break-glass is disabled"
   ```

### Step 6: Post-incident review

Within 48 hours of the break-glass invocation, a post-incident review
MUST be conducted. The review covers:

- Why the authority was down (root cause)
- Whether the break-glass was necessary (could the action have waited?)
- Whether the break-glass procedure was followed correctly
- Any receipts emitted with `break_glass=true` (review each one)
- Whether the break-glass key was properly decommissioned
- Recommendations for preventing the authority outage

The review is attended by:
- The operator who invoked the break-glass
- The operator who approved it
- The engineering lead
- The CISO (or delegate)

## Break-glass key management

The break-glass key is a separate Ed25519 key from the authority's
signing key. It is:

- Stored in a sealed envelope (KMS or HSM, never on disk in plaintext)
- Only accessible to the authorized operators
- Rotated every 30 days
- Disabled when not in use (must be explicitly enabled for each invocation)
- Tracked in an audit log (every enable/disable is recorded)

The break-glass key's lifecycle states (per the key-lifecycle state
machine) are:

- `active` — key can sign break-glass proofs (only during an active
  break-glass invocation)
- `suspended` — key is temporarily disabled (default state)
- `revoked` — key is permanently disabled (after rotation or compromise)

The key MUST be in `suspended` state by default. It is moved to `active`
only for the duration of a break-glass invocation, then moved back to
`suspended`.

## Monitoring and alerting

The following alerts MUST be configured:

| Alert | Threshold | Severity |
|---|---|---|
| Break-glass key enabled | Any enable event | Page (P2) |
| Break-glass proof minted | Any mint event | Page (P1) |
| Break-glass key enabled > 5 minutes | Duration threshold | Page (P1) |
| Break-glass key not suspended after invocation | Any event | Page (P1) |
| Break-glass proof used more than once | Replay detection | Page (P0 — security incident) |

Every break-glass alert pages the on-call SRE AND the on-call security
engineer. Break-glass is a tier-0 operation; it is never silently
ignored.

## Receipt-emitting exception

The key design principle (from Fable 5's Aoife persona):

> "the break-glass itself emitting receipts so the exception is as
> auditable as the rule"

Every break-glass invocation produces:

1. A **break-glass proof** (signed by the break-glass key, marked
   `break_glass=true`)
2. A **receipt** (same structure as a normal receipt, but with
   `break_glass=true` in the metadata)
3. A **break-glass log entry** (the structured record from Step 2)

All three are retained for the same duration as normal receipts (90 days
pilot, 7 years production). An auditor reviewing the evidence store can
filter for `break_glass=true` to see every exception that was made.

This is what makes the break-glass safe: the exception is not a hole in
the audit trail; it is a marked, reviewable, time-bounded entry in the
same trail.

## See also

- [Pilot Approval Conditions](PILOT_APPROVAL_CONDITIONS.md) — Condition 4
  requires this runbook
- [CONTROL_PLANE_RELEASE_READINESS.md](CONTROL_PLANE_RELEASE_READINESS.md) —
  the authority-down case is listed as a Red blocker
- [KMS_ROTATION_RUNBOOK.md](../actenon-kernel/docs/reference/ecosystem/KMS_ROTATION_RUNBOOK.md) —
  the break-glass key follows the same lifecycle as the authority key

---

*This runbook is the artifact Fable 5's review offered to "turn your
biggest operational objection into a product feature." The break-glass
that emits receipts is the difference between "we failed closed and the
SRE bypassed it at 3am with no audit trail" and "we failed closed, the
SRE invoked a controlled exception, and every step is reviewable."*
