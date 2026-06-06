# Hosted Pilot Verification Checklist

## Purpose

This checklist defines the minimum post-deploy and post-restart verification flow for a managed single-tenant Actenon Cloud hosted pilot.

It is intended for internal operators. It does not imply self-serve cloud readiness.

Use it after:

- first environment bring-up
- new release deployment
- runtime restart
- incident recovery action

## 1. Endpoint Reachability

- [ ] The pilot hostname resolves correctly.
- [ ] TLS terminates successfully at the hosted endpoint.
- [ ] The reverse proxy or ingress forwards requests to the app runtime.

Suggested checks:

```bash
curl -i https://<pilot-hostname>/api/v1/health/live
```

## 2. Health Verification

- [ ] `GET /api/v1/health/live` returns `200`.
- [ ] `GET /api/v1/health/ready` returns `200`.
- [ ] Readiness reports `database=ready`.
- [ ] Readiness reports `evidence_storage=ready`.

If readiness fails, do not treat the environment as fit for pilot traffic.

## 3. Metrics Verification

- [ ] `GET /metrics` returns `200`.
- [ ] The response is Prometheus text output.
- [ ] `action_control_plane_runtime_ready` is `1`.
- [ ] `action_control_plane_dependency_ready{check_name="database"}` is `1`.
- [ ] `action_control_plane_dependency_ready{check_name="evidence_storage"}` is `1`.
- [ ] At least one `action_control_plane_http_requests_total` sample is present after probing health endpoints.

Suggested check:

```bash
curl -s https://<pilot-hostname>/metrics | rg 'action_control_plane_(runtime_ready|dependency_ready|http_requests_total)'
```

## 4. Correlation Verification

- [ ] A request returns `X-Request-ID`.
- [ ] A request returns `X-Correlation-ID`.
- [ ] A request returns `X-Trace-ID`.
- [ ] The same identifiers are searchable in the central log sink.

Suggested check:

```bash
curl -i \
  -H 'X-Request-ID: verify-request-1' \
  -H 'X-Correlation-ID: verify-correlation-1' \
  https://<pilot-hostname>/api/v1/health/live
```

## 5. Startup Verification

Confirm the log sink contains:

- [ ] `runtime.startup.begin`
- [ ] `runtime.startup.check` with `check_name=database`
- [ ] `runtime.startup.check` with `check_name=evidence_storage`
- [ ] `runtime.config.loaded`
- [ ] `runtime.observability.profile`
- [ ] `runtime.startup.complete`

If startup failed, look for:

- `runtime.configuration.invalid`
- `runtime.startup.failed`

## 6. Pilot Workflow Surface Verification

- [ ] `/pilot/actions` loads.
- [ ] `/pilot/review` loads.
- [ ] One action detail page loads.
- [ ] One audit trace export succeeds.

If practical in the environment, also verify one representative mutation path:

- [ ] one approval decision succeeds
- [ ] or one evidence upload succeeds

That confirms workflow logs and counters are being exercised, not just static pages.

## 7. Storage And Database Verification

- [ ] The configured PostgreSQL database is reachable from the app runtime.
- [ ] The evidence storage mount exists and is writable.
- [ ] The current migration revision is at head.

## 8. Log Visibility Verification

- [ ] Application logs are visible centrally.
- [ ] Reverse proxy logs are visible centrally if used.
- [ ] Operators can search by `request_id`, `correlation_id`, and `action_intent_record_id`.
- [ ] Workflow event families such as `approval.decision.recorded` and `receipt.ingested` are visible when those actions occur.

## 9. Before Accepting Pilot Traffic

- [ ] The current environment is understood as a managed hosted pilot, not a broad hosted product.
- [ ] Named operator and engineering owners are on point.
- [ ] Current maturity limits are understood:
  - auth remains early unless separately upgraded
  - signing remains early unless separately upgraded
  - evidence storage is filesystem-backed
  - observability is logs plus in-process metrics, not dashboards plus alerting
  - verifier responsibilities remain outside this repo
