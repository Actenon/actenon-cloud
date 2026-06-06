# Internal Observability

## Purpose

This document defines the minimum internal observability surface for a managed single-tenant Actenon Cloud invoice payment pilot.

It is intentionally narrow. It does not claim a full production observability platform.

## Scope Boundary

Customer-facing action visibility and internal service observability are different surfaces.

Customer-facing traceability answers:

- what happened to this invoice payment action
- why it was allowed, held, or refused
- which approvals, evidence objects, proofs, and receipts are linked to it

Internal observability answers:

- is the runtime up
- is it ready to serve traffic
- which dependency is failing
- which request or workflow mutation failed
- which tenant, principal, and action record were involved

This document covers only the second category.

## What The Runtime Provides Now

The current hosted pilot runtime now provides:

- structured application logs
- request, correlation, and trace identifiers on every response
- startup and readiness logs
- workflow mutation logs for intake, approval decisions, evidence mutations, proof issuance, and receipt ingestion
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /metrics` in Prometheus text format

This is enough for pilot operators to diagnose most runtime and workflow failures without claiming mature distributed tracing or dashboards.

## Structured Logging

Application logs are emitted to standard output and are designed for forwarding into a central log sink.

### Core Request Events

- `request.completed`
- `request.failed`

These logs include:

- `request_id`
- `correlation_id`
- `trace_id`
- `method`
- `path`
- `path_template`
- `status_code`
- `duration_ms`
- `principal_type`
- `principal_id`
- `tenant_id` or `tenant_ids` where the request context makes that known
- `action_intent_record_id` where the route exposes it
- `outcome`

### Runtime Events

- `runtime.startup.begin`
- `runtime.startup.check`
- `runtime.config.loaded`
- `runtime.observability.profile`
- `runtime.startup.complete`
- `runtime.startup.failed`
- `runtime.shutdown.complete`

### Workflow Mutation Events

- `action_intent.intake.completed`
- `action_intent.intake.replayed`
- `action_intent.intake.failed`
- `approval.decision.recorded`
- `approval.decision.failed`
- `evidence.registered`
- `evidence.register.failed`
- `evidence.uploaded`
- `evidence.upload.failed`
- `proof.issuance.completed`
- `proof.issuance.replayed`
- `proof.issuance.rejected`
- `proof.issuance.failed`
- `receipt.ingested`
- `receipt.ingestion.replayed`
- `receipt.ingestion.failed`

These logs include the high-value identifiers operators need for diagnosis:

- `tenant_id`
- `principal_type`
- `principal_id`
- `action_intent_record_id`
- mutation-specific ids such as `approval_request_id`, `evidence_object_id`, `issued_proof_id`, or `receipt_id`
- `outcome`
- `duration_ms`

## Correlation Headers

The runtime now supports three correlation values:

- `X-Request-ID`
- `X-Correlation-ID`
- `X-Trace-ID`

Behavior:

- inbound `X-Request-ID` is accepted or generated if absent
- inbound `X-Correlation-ID` is accepted or defaults to the request id
- inbound `traceparent` is accepted when present, and the trace id portion is exposed as `X-Trace-ID`
- if no `traceparent` is supplied, the runtime derives a stable trace id from the correlation id

These same values are included in request-scoped structured logs.

This is a correlation layer, not full distributed tracing.

## Metrics Endpoint

The runtime exposes:

- `GET /metrics`

It returns Prometheus text exposition from an in-process registry.

### Current Metric Families

- `action_control_plane_http_requests_total`
- `action_control_plane_http_request_duration_seconds`
- `action_control_plane_http_requests_in_progress`
- `action_control_plane_runtime_ready`
- `action_control_plane_dependency_ready`
- `action_control_plane_runtime_info`
- `action_control_plane_process_started_time_seconds`
- `action_control_plane_action_intake_total`
- `action_control_plane_approval_decisions_total`
- `action_control_plane_evidence_mutations_total`
- `action_control_plane_proof_issuance_total`
- `action_control_plane_receipt_ingestions_total`
- `action_control_plane_transparency_log_leaves_total`
- `action_control_plane_transparency_checkpoints_total`
- `action_control_plane_transparency_tree_size`
- `action_control_plane_transparency_integrity_failures_total`

### What These Metrics Are For

- HTTP counters and latency help separate runtime-wide request failure from single-record workflow failure.
- Runtime and dependency gauges show whether the app is healthy enough to accept pilot traffic.
- Workflow counters show whether the core invoice payment control path is progressing, replaying idempotently, or rejecting work.
- Transparency metrics show append and checkpoint progress and expose any detected integrity failure for immediate alerting.

### What These Metrics Are Not

- not a dashboard product
- not a tracing backend
- not an alerting system
- not long-term metrics storage

## Health Model

The current health model is:

- `live`: process is responding to HTTP
- `ready`: process plus database plus filesystem-backed evidence storage

`ready` does not verify:

- the separate Actenon Kernel verifier boundary
- external receipt providers
- managed signing infrastructure
- backup integrity

## Hosted Pilot Operator Use

Use this internal signal order after deploy, restart, or incident:

1. Confirm the pilot hostname and TLS ingress are reachable.
2. Check `GET /api/v1/health/live`.
3. Check `GET /api/v1/health/ready`.
4. Check `GET /metrics` for runtime and dependency gauges.
5. Search logs by `request_id`, `correlation_id`, or `action_intent_record_id`.
6. Pivot into workflow mutation events for the affected action.

Related docs:

- `HOSTED_PILOT_VERIFICATION_CHECKLIST.md`
- `INCIDENT_TRIAGE_RUNBOOK.md`
- `OPERATIONS_RUNBOOK.md`

## Current Limits

This pass does not provide:

- distributed tracing export
- metrics scraping configuration or dashboards
- alert routing
- automated incident detection
- backup verification telemetry
- dependency probes for external verifier or bank/provider systems

That is intentional. The current observability surface is meant to make a managed pilot diagnosable, not to imply full production SaaS maturity.
