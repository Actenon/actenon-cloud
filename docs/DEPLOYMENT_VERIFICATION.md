# Deployment Verification

## Purpose

This document defines the minimum verification checklist for a managed single-tenant pilot deployment after a new Actenon Cloud release is started.

For the broader hosted pilot operational check after deploy or restart, also use:

- `HOSTED_PILOT_VERIFICATION_CHECKLIST.md`

## Runtime Verification

Verify liveness:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health/live
```

Verify readiness:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health/ready
```

Expected readiness shape:

- `checks.database=ready`
- `checks.evidence_storage=ready`
- `status=ready`

## Startup Log Verification

Confirm the log stream contains:

- `runtime.config.loaded`
- `runtime.startup.check` with `check_name=database`
- `runtime.startup.check` with `check_name=evidence_storage`
- `runtime.startup.complete`

If the deployment fails, look for:

- `runtime.configuration.invalid`
- `runtime.startup.failed`
- `request.failed`

## Functional Pilot Verification

Run the minimum functional checks:

1. Open the invoice payment queue at `/pilot/actions`.
2. Confirm the held and exceptions queue loads at `/pilot/review`.
3. Bootstrap or verify an operator session if the environment allows it.
4. Create or inspect one known Action Intent record.
5. Confirm the action detail page renders lifecycle state and artifacts.
6. Verify one audit trace fetch succeeds.

## Storage Verification

Confirm:

- the evidence storage directory exists inside the runtime
- the service can write to it
- readiness returns `evidence_storage=ready`

## Database Verification

Confirm:

- migrations applied successfully
- readiness returns `database=ready`
- the app can read and write expected pilot data

## What This Does Not Verify

This checklist does not prove:

- enterprise identity maturity
- managed signing maturity
- real capability release integration
- production-scale observability
- verifier integration correctness beyond external dependency availability
