# Release Deploy Runbook

## Purpose

This runbook defines the minimum safe release flow for a managed single-tenant Actenon Cloud pilot deployment.

It is intentionally lightweight. It is not a production change-management framework.

## Preconditions

- non-default secrets are prepared
- target database is reachable
- mounted persistent evidence storage is provisioned and writable
- the target image or local build is available
- one named engineering owner and one named pilot operator are available

## Pre-Deploy Checks

1. Confirm the target environment matches the expected pilot profile.
2. Confirm the database connection string points at the intended pilot database.
3. Confirm the evidence storage mount exists and is writable by the application user.
4. Confirm `ACTION_CONTROL_PLANE_ENABLE_DOCS=false` unless the environment is an intentionally protected sandbox.
5. Confirm the separate verifier dependency, if needed by the workflow, is still treated as external to this deployment.

## Deployment Sequence

1. Pull or build the target application image.
2. Render the deployment configuration and confirm environment values.
3. Start or verify PostgreSQL readiness.
4. Run migrations before switching the app to live traffic.
5. Start the web service.
6. Verify `GET /api/v1/health/live`.
7. Verify `GET /api/v1/health/ready`.
8. Verify that startup logs include:
   - `runtime.config.loaded`
   - `runtime.startup.check` for `database`
   - `runtime.startup.check` for `evidence_storage`
   - `runtime.startup.complete`
9. Run the deployment verification checklist in [DEPLOYMENT_VERIFICATION.md](DEPLOYMENT_VERIFICATION.md).
10. Run the hosted pilot verification checklist in [HOSTED_PILOT_VERIFICATION_CHECKLIST.md](HOSTED_PILOT_VERIFICATION_CHECKLIST.md).

## Migration Safety

1. Back up the pilot database before schema changes.
2. Never start mutating pilot traffic until migrations succeed.
3. If migrations fail, do not start the app container.
4. If the app starts but readiness fails after migration, treat the deployment as failed.
5. Record the migration revision and deployment timestamp in deployment notes.

## Rollback Trigger Conditions

Roll back or stop the rollout if:

- migrations fail
- startup logs show `runtime.configuration.invalid` or `runtime.startup.failed`
- readiness returns `not_ready`
- the evidence storage check fails
- auth bootstrap or pilot action smoke checks fail

## Rollback Actions

1. Stop or remove the new app container.
2. Return traffic to the previous working deployment if one exists.
3. Restore the database only with explicit operator approval if the schema or data state requires it.
4. Re-check readiness and core pilot flows after rollback.
5. Record the incident and the rollback reason.

## Known Limits

- this runbook does not yet provide automated rollout or rollback tooling
- this runbook does not replace backup or disaster recovery procedures
- signing and capability release remain pilot-stage and must be treated accordingly
