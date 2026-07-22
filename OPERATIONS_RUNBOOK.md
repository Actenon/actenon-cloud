# Operations Runbook

## Purpose

This runbook is a skeleton for internal development and design-partner pilot operations. It is not yet a production on-call manual.

Use it together with:

- `INTERNAL_OBSERVABILITY.md`
- `HOSTED_PILOT_VERIFICATION_CHECKLIST.md`
- `INCIDENT_TRIAGE_RUNBOOK.md`
- `HOSTED_PILOT_TOPOLOGY.md`
- `SINGLE_TENANT_DEPLOYMENT_MODEL.md`

## Health Checks

1. Check `GET /api/v1/health/live`.
2. Check `GET /api/v1/health/ready`.
3. Confirm database connectivity.
4. Confirm evidence storage is mounted and writable.
5. Confirm recent structured logs are arriving in the expected sink.

## Routine Startup

1. Load non-default environment variables and secrets.
2. Confirm the managed database target is the intended pilot database.
3. Confirm the evidence storage path is mounted and writable.
4. Run migrations before starting live traffic.
5. Start the web runtime.
6. Confirm liveness and readiness.
7. Confirm startup logs show `runtime.config.loaded` and both startup checks.
8. Confirm centralized logs are receiving fresh app events.
9. Use only the approved operator bootstrap or token bring-up flow for that environment.

For the current hosted pilot model:

- migration timing is operator-controlled
- rollback decisions are operator-controlled
- first-operator bootstrap remains a supervised operator task

## Incident Triage

1. Identify affected tenant, action intent, proof, escrow record, or receipt.
2. Query `/api/v1/audit/traces/{action_intent_record_id}` when an Action Intent trace is available.
3. Review reconciliation records and receipt linkage.
4. Determine whether the issue is intake, approval, evidence, issuance, escrow, or receipt-related.
5. If release behavior is involved, confirm whether the path was simulated or externally integrated.

For the hosted pilot triage sequence, use `INCIDENT_TRIAGE_RUNBOOK.md`.

## Migration Safety

1. Back up the managed database before pilot schema changes.
2. Apply migrations in a staging-like environment first.
3. Verify `GET /api/v1/health/ready` after migration.
4. Verify readiness includes `database=ready` and `evidence_storage=ready`.
5. Verify the evidence mount still resolves to the expected persistent path.
6. Smoke-test auth, intake, issuance, escrow, and receipt ingestion.

## Rollback

1. Stop further mutating traffic if the issue is high risk.
2. Use deployment rollback if available.
3. Restore the previous database state only with explicit operator approval and audit notes.
4. Restore or reconcile evidence files only through the defined backup process for that pilot.
5. Reconcile any partially issued proofs or escrow records after rollback.

## Known Limits

- metrics, tracing, and alerting are not fully implemented
- capability release is still simulated unless an external integration is added later
- signing is still development-local unless upgraded in a future pass
- this runbook does not yet define a complete hosted operator bootstrap procedure
- this runbook does not yet define backup, restore, or disaster recovery execution details
