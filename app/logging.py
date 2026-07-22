from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from app.config import Settings

REQUEST_ID_CONTEXT: ContextVar[str | None] = ContextVar("request_id", default=None)
CORRELATION_ID_CONTEXT: ContextVar[str | None] = ContextVar("correlation_id", default=None)
TRACE_ID_CONTEXT: ContextVar[str | None] = ContextVar("trace_id", default=None)


def set_request_id(request_id: str) -> Token[str | None]:
    return REQUEST_ID_CONTEXT.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    REQUEST_ID_CONTEXT.reset(token)


def get_request_id() -> str | None:
    return REQUEST_ID_CONTEXT.get()


def set_correlation_id(correlation_id: str) -> Token[str | None]:
    return CORRELATION_ID_CONTEXT.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    CORRELATION_ID_CONTEXT.reset(token)


def get_correlation_id() -> str | None:
    return CORRELATION_ID_CONTEXT.get()


def set_trace_id(trace_id: str) -> Token[str | None]:
    return TRACE_ID_CONTEXT.set(trace_id)


def reset_trace_id(token: Token[str | None]) -> None:
    TRACE_ID_CONTEXT.reset(token)


def get_trace_id() -> str | None:
    return TRACE_ID_CONTEXT.get()


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
            "trace_id": get_trace_id(),
        }

        for field_name in (
            "event",
            "service",
            "environment",
            "version",
            "component",
            "method",
            "path",
            "path_template",
            "status_code",
            "duration_ms",
            "check_name",
            "check_status",
            "startup_phase",
            "error_class",
            "error_message",
            "database_status",
            "database_backend",
            "evidence_storage_root",
            "logging_backend",
            "metrics_backend",
            "tracing_backend",
            "health_model",
            "simulation_boundary",
            "docs_enabled",
            "auth_mode",
            "capability_release_mode",
            "tenant_id",
            "tenant_ids",
            "principal_type",
            "principal_id",
            "action_intent_record_id",
            "approval_request_id",
            "approval_state",
            "decision",
            "decision_state",
            "evidence_object_id",
            "evidence_state",
            "evidence_type",
            "execution_state",
            "idempotent_replay",
            "issued_proof_id",
            "outcome",
            "proof_kind",
            "proof_status",
            "receipt_id",
            "receipt_state",
            "storage_mode",
            "contract_validation_status",
        ):
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, sort_keys=True)


def configure_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(settings.log_level)

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s",
                "%Y-%m-%dT%H:%M:%S%z",
            )
        )

    root_logger.addHandler(handler)
    logging.captureWarnings(True)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
