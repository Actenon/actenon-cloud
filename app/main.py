from __future__ import annotations

import hashlib
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import Settings, get_settings
from app.container import ApplicationContainer
from app.logging import (
    configure_logging,
    reset_correlation_id,
    reset_request_id,
    reset_trace_id,
    set_correlation_id,
    set_request_id,
    set_trace_id,
)
from app.metrics import initialize_runtime_metrics, reset_metrics_registry
from app.pilot_ui.routes import router as pilot_ui_router

logger = logging.getLogger("action_control_plane.http")
runtime_logger = logging.getLogger("action_control_plane.runtime")
PILOT_UI_STATIC_DIR = Path(__file__).resolve().parent / "pilot_ui" / "static"
TRACEPARENT_PATTERN = re.compile(
    r"^[\da-f]{2}-([\da-f]{32})-[\da-f]{16}-[\da-f]{2}$",
    re.IGNORECASE,
)


def _configure_otel(app: FastAPI, settings: Settings) -> None:
    """Optionally instrument the app with OpenTelemetry tracing.

    Fails closed: if ``opentelemetry`` or
    ``opentelemetry.instrumentation.fastapi`` is not installed, or if
    instrumentation raises for any reason, the app continues to run
    without tracing. This keeps OTel an optional observability addon.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanProcessor
    except ImportError:
        runtime_logger.info(
            "runtime.otel.skipped",
            extra={
                "event": "runtime.otel.skipped",
                "service": settings.service_slug,
                "environment": settings.environment,
                "component": "observability",
                "reason": "opentelemetry not installed",
            },
        )
        return

    try:
        resource = Resource.create(
            {
                "service.name": settings.service_slug,
                "service.version": settings.version,
                "deployment.environment": settings.environment,
            }
        )
        provider = TracerProvider(resource=resource)
        # Default to a console span processor. Production deployments should
        # configure OTLP via OTEL_EXPORTER_OTLP_ENDPOINT and add an
        # OTLPSpanProcessor in addition to (or instead of) this one.
        provider.add_span_processor(ConsoleSpanProcessor())
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        runtime_logger.info(
            "runtime.otel.instrumented",
            extra={
                "event": "runtime.otel.instrumented",
                "service": settings.service_slug,
                "environment": settings.environment,
                "component": "observability",
            },
        )
    except Exception as exc:
        runtime_logger.warning(
            "runtime.otel.instrumentation_failed",
            extra={
                "event": "runtime.otel.instrumentation_failed",
                "service": settings.service_slug,
                "environment": settings.environment,
                "component": "observability",
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )


def _extract_trace_id(traceparent: str | None, fallback_seed: str) -> str:
    if traceparent:
        match = TRACEPARENT_PATTERN.match(traceparent.strip())
        if match:
            return match.group(1).lower()
    return hashlib.sha256(fallback_seed.encode("utf-8")).hexdigest()[:32]


def _path_template_for_request(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if not template:
        return "unmatched"
    # Starlette route.path does NOT include the router prefix when mounted
    # via include_router(prefix=...). Reconstruct the full template by
    # finding where the route-level template matches in the actual path.
    actual_path = request.scope.get("path", "")
    if not actual_path:
        return str(template)
    # Convert template {param} placeholders to a regex that matches any
    # path segment, then find where the template matches at the end of
    # the actual path. The prefix is everything before that match.
    import re as _re
    pattern = _re.sub(r"\{[^}]+\}", r"[^/]+", template)
    match = _re.search(pattern + r"$", actual_path)
    if match:
        return actual_path[: match.start()] + template
    return str(template)


def _request_log_fields(request: Request) -> dict[str, object]:
    fields: dict[str, object] = {}
    tenant_id = request.path_params.get("tenant_id") or request.query_params.get("tenant_id")
    action_intent_record_id = (
        request.path_params.get("action_intent_record_id")
        or request.query_params.get("action_intent_record_id")
    )
    if tenant_id:
        fields["tenant_id"] = tenant_id
    if action_intent_record_id:
        fields["action_intent_record_id"] = action_intent_record_id

    auth_session = getattr(request.state, "auth_session", None)
    if auth_session is not None:
        fields["principal_type"] = auth_session.principal_type
        fields["principal_id"] = auth_session.principal_id
        if auth_session.tenant_ids:
            fields["tenant_ids"] = list(auth_session.tenant_ids)
            if "tenant_id" not in fields and len(auth_session.tenant_ids) == 1:
                fields["tenant_id"] = auth_session.tenant_ids[0]
    return fields


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    reset_metrics_registry()
    metrics_registry = initialize_runtime_metrics()
    configure_logging(runtime_settings)
    try:
        runtime_settings.validate_environment()
    except Exception as exc:
        runtime_logger.exception(
            "runtime.configuration.invalid",
            extra={
                "event": "runtime.configuration.invalid",
                "service": runtime_settings.service_slug,
                "environment": runtime_settings.environment,
                "component": "runtime",
                "version": runtime_settings.version,
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        raise

    container = ApplicationContainer.from_settings(runtime_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container
        container.startup()
        try:
            yield
        finally:
            container.shutdown()

    docs_url = f"{runtime_settings.api_v1_prefix}/docs" if runtime_settings.enable_docs else None
    openapi_url = (
        f"{runtime_settings.api_v1_prefix}/openapi.json" if runtime_settings.enable_docs else None
    )

    app = FastAPI(
        title=runtime_settings.service_name,
        version=runtime_settings.version,
        docs_url=docs_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix=runtime_settings.api_v1_prefix)
    app.include_router(pilot_ui_router)
    app.mount("/pilot-static", StaticFiles(directory=PILOT_UI_STATIC_DIR), name="pilot-static")

    # Optional OpenTelemetry tracing — fails closed if not installed.
    _configure_otel(app, runtime_settings)

    @app.get("/metrics", include_in_schema=False)
    def get_metrics() -> PlainTextResponse:
        container.readiness_checks()
        return PlainTextResponse(
            metrics_registry.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid4().hex)
        correlation_id = request.headers.get("X-Correlation-ID", request_id)
        trace_id = _extract_trace_id(request.headers.get("traceparent"), correlation_id)
        request_id_token = set_request_id(request_id)
        correlation_id_token = set_correlation_id(correlation_id)
        trace_id_token = set_trace_id(trace_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id
        started = perf_counter()
        http_in_progress = metrics_registry.gauge(
            "action_control_plane_http_requests_in_progress",
            "Current number of in-flight HTTP requests handled by the app runtime.",
        )
        http_requests_total = metrics_registry.counter(
            "action_control_plane_http_requests_total",
            "Count of completed HTTP requests served by the app runtime.",
            label_names=("method", "path_template", "status_code"),
        )
        http_request_duration = metrics_registry.histogram(
            "action_control_plane_http_request_duration_seconds",
            "HTTP request duration in seconds by method, path template, and response status.",
            label_names=("method", "path_template", "status_code"),
        )
        http_in_progress.inc()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            path_template = _path_template_for_request(request)
            status_code = 500
            logger.exception(
                "request.failed",
                extra={
                    "event": "request.failed",
                    "service": runtime_settings.service_slug,
                    "environment": runtime_settings.environment,
                    "method": request.method,
                    "path": request.url.path,
                    "path_template": path_template,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                    "outcome": "error",
                    **_request_log_fields(request),
                },
            )
            http_requests_total.inc(
                method=request.method,
                path_template=path_template,
                status_code=str(status_code),
            )
            http_request_duration.observe(
                duration_ms / 1000,
                method=request.method,
                path_template=path_template,
                status_code=str(status_code),
            )
            http_in_progress.dec()
            reset_trace_id(trace_id_token)
            reset_correlation_id(correlation_id_token)
            reset_request_id(request_id_token)
            raise

        duration_ms = int((perf_counter() - started) * 1000)
        path_template = _path_template_for_request(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Trace-ID"] = trace_id
        logger.info(
            "request.completed",
            extra={
                "event": "request.completed",
                "service": runtime_settings.service_slug,
                "environment": runtime_settings.environment,
                "method": request.method,
                "path": request.url.path,
                "path_template": path_template,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "outcome": "success" if response.status_code < 500 else "error",
                **_request_log_fields(request),
            },
        )
        http_requests_total.inc(
            method=request.method,
            path_template=path_template,
            status_code=str(response.status_code),
        )
        http_request_duration.observe(
            duration_ms / 1000,
            method=request.method,
            path_template=path_template,
            status_code=str(response.status_code),
        )
        http_in_progress.dec()
        reset_trace_id(trace_id_token)
        reset_correlation_id(correlation_id_token)
        reset_request_id(request_id_token)
        return response

    return app


app = create_app()
