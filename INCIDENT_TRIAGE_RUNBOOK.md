# Incident Triage Runbook

## Purpose

This runbook defines the minimum incident-triage path for a managed single-tenant Actenon Cloud invoice payment pilot.

It is intended for internal operators. It does not assume mature dashboards, distributed tracing, or automated incident response.

## First Questions

Answer these in order:

1. Is the hosted endpoint reachable?
2. Is the runtime live?
3. Is the runtime ready?
4. Is the issue global or isolated to one request or action record?
5. Is the problem in this control-plane repo or at an external dependency boundary?

## Evidence To Gather First

Collect these before making conclusions:

- pilot hostname
- environment name
- time window
- `X-Request-ID` if available
- `X-Correlation-ID` if available
- `X-Trace-ID` if available
- affected `tenant_id`
- affected `action_intent_record_id`
- affected `approval_request_id`, `evidence_object_id`, `issued_proof_id`, or `receipt_id` if relevant
- `GET /api/v1/health/ready` output
- a `/metrics` snapshot

## Fast Triage Flow

### A. Ingress Or Endpoint Failure

Symptoms:

- TLS failure
- reverse proxy timeout
- `502` or `503` before the app runtime

Check:

- ingress or reverse proxy logs
- app container status
- `GET /api/v1/health/live`

Likely boundary:

- ingress
- container runtime
- deployment configuration

### B. Runtime Live But Not Ready

Symptoms:

- `live` returns `200`
- `ready` returns `503`

Check:

- readiness details for `database` and `evidence_storage`
- `action_control_plane_runtime_ready`
- `action_control_plane_dependency_ready`
- startup logs around the most recent restart

Likely boundary:

- database connectivity
- filesystem-backed evidence mount
- runtime configuration

### C. Request-Level Failure

Symptoms:

- one API call returns `5xx`
- the pilot UI partially loads or fails during mutation

Check:

- response headers: `X-Request-ID`, `X-Correlation-ID`, `X-Trace-ID`
- `request.failed` logs
- matching `request.completed` or `request.failed` by `path_template`
- `action_control_plane_http_requests_total`
- `action_control_plane_http_request_duration_seconds`

Likely boundary:

- one backend route
- bad input or state transition
- dependency failure on a specific path

### D. Workflow Mutation Failure

Symptoms:

- one invoice payment action is stuck
- approvals do not progress
- evidence upload or registration fails
- proof issuance rejects unexpectedly
- receipt ingestion fails or leaves the action in an unexpected state

Check the workflow event family that matches the failing step:

- `action_intent.intake.*`
- `approval.decision.*`
- `evidence.register*`
- `evidence.upload*`
- `proof.issuance.*`
- `receipt.ingestion.*`
- `receipt.ingested`

Correlate those logs using:

- `tenant_id`
- `principal_id`
- `action_intent_record_id`
- the mutation-specific record id

Also check the workflow counters:

- `action_control_plane_action_intake_total`
- `action_control_plane_approval_decisions_total`
- `action_control_plane_evidence_mutations_total`
- `action_control_plane_proof_issuance_total`
- `action_control_plane_receipt_ingestions_total`

Likely boundary:

- application state transition logic
- data integrity or sequencing
- external receipt arrival timing

### E. External Dependency Boundary

Symptoms:

- control-plane state looks consistent but external verification or execution expectations do not
- provider or verifier behavior diverges from what the control plane recorded

Check:

- whether the failure is actually within this repo's responsibility
- whether the issue belongs to:
  - the separate verifier dependency or repo
  - a payment or treasury provider boundary
  - a deployment or operator process outside the app runtime

Do not classify verifier or provider issues as control-plane bugs without evidence.

## How To Use `/metrics` During Triage

Use `/metrics` to separate broad runtime failure from isolated workflow failure:

- if `action_control_plane_runtime_ready` is `0`, treat the incident as environment health first
- if readiness gauges are `1` but HTTP failures spike, treat it as a route or code-path problem
- if HTTP metrics look stable but a workflow counter stops moving or shifts to error-heavy outcomes, treat it as a workflow-specific issue

`/metrics` is a live snapshot, not a historical source of truth. Pair it with logs.

## Containment Guidance

- Stop mutating invoice payment actions if the failure could produce unsafe operational outcomes.
- Do not continue deployment or migration work while readiness is failing.
- If the incident is limited to one tenant or one action record, avoid escalating it as a full environment outage without evidence.
- If the incident is outside this repo's boundary, record that clearly and hand off to the right owner.

## Recovery Checks

Before declaring mitigation complete, confirm:

- `GET /api/v1/health/live` returns `200`
- `GET /api/v1/health/ready` returns `200`
- `GET /metrics` shows `action_control_plane_runtime_ready 1`
- central logs show no ongoing `runtime.startup.failed` or `request.failed` events for the affected path
- one representative pilot UI route loads
- one affected workflow path succeeds or is truthfully refused as expected

## Known Blind Spots

This runbook still assumes:

- no tracing backend
- no dashboards
- no alert routing
- no automated verifier dependency probe
- no automated backup or restore verification

Use it together with:

- `INTERNAL_OBSERVABILITY.md`
- `HOSTED_PILOT_VERIFICATION_CHECKLIST.md`
- `OPERATIONS_RUNBOOK.md`
