from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from app.config import Settings, ensure_writable_directory
from app.database import Database
from app.metrics import get_metrics_registry, initialize_runtime_metrics, set_process_started_at
from app.telemetry import build_observability_profile

logger = logging.getLogger("action_control_plane.runtime")


@dataclass(frozen=True, slots=True)
class RuntimeCheckResult:
    status: Literal["ready", "not_ready"]
    detail: str


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    database: Database
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_settings(cls, settings: Settings) -> ApplicationContainer:
        return cls(settings=settings, database=Database(settings.database_url))

    def startup(self) -> None:
        startup_phase = "initialize"
        metrics_registry = initialize_runtime_metrics()
        metrics_registry.gauge(
            "action_control_plane_runtime_ready",
            "Whether the current runtime instance is ready to accept pilot traffic.",
        ).set(0)
        metrics_registry.gauge(
            "action_control_plane_runtime_info",
            "Static metadata about the running Actenon Cloud control-plane instance.",
            label_names=(
                "service",
                "environment",
                "version",
                "auth_mode",
                "capability_release_mode",
            ),
        ).set(
            1,
            service=self.settings.service_slug,
            environment=self.settings.environment,
            version=self.settings.version,
            auth_mode=self.settings.auth_mode,
            capability_release_mode=self.settings.capability_release_mode,
        )
        set_process_started_at(self.started_at.timestamp())
        logger.info(
            "runtime.startup.begin",
            extra={
                "event": "runtime.startup.begin",
                "service": self.settings.service_slug,
                "environment": self.settings.environment,
                "component": "runtime",
                "version": self.settings.version,
            },
        )
        try:
            startup_phase = "database_connect"
            self.database.connect()
            logger.info(
                "runtime.startup.check",
                extra={
                    "event": "runtime.startup.check",
                    "service": self.settings.service_slug,
                    "environment": self.settings.environment,
                    "component": "runtime",
                    "check_name": "database",
                    "check_status": "ready",
                    "database_backend": self.settings.database_backend(),
                },
            )

            startup_phase = "evidence_storage_probe"
            evidence_storage_root = ensure_writable_directory(
                self.settings.evidence_storage_root,
                create=True,
            )
            logger.info(
                "runtime.startup.check",
                extra={
                    "event": "runtime.startup.check",
                    "service": self.settings.service_slug,
                    "environment": self.settings.environment,
                    "component": "runtime",
                    "check_name": "evidence_storage",
                    "check_status": "ready",
                    "evidence_storage_root": str(evidence_storage_root),
                },
            )

            startup_phase = "observability_profile"
            observability_profile = build_observability_profile(self.settings)
            logger.info(
                "runtime.config.loaded",
                extra={
                    "event": "runtime.config.loaded",
                    "service": self.settings.service_slug,
                    "environment": self.settings.environment,
                    "component": "runtime",
                    "version": self.settings.version,
                    "docs_enabled": self.settings.enable_docs,
                    "database_backend": self.settings.database_backend(),
                    "auth_mode": self.settings.auth_mode,
                    "capability_release_mode": self.settings.capability_release_mode,
                    "evidence_storage_root": str(evidence_storage_root),
                },
            )
            logger.info(
                "runtime.observability.profile",
                extra={
                    "event": "runtime.observability.profile",
                    "service": self.settings.service_slug,
                    "environment": self.settings.environment,
                    "component": "observability",
                    **observability_profile.to_log_fields(),
                },
            )
            logger.info(
                "runtime.startup.complete",
                extra={
                    "event": "runtime.startup.complete",
                    "service": self.settings.service_slug,
                    "environment": self.settings.environment,
                    "component": "runtime",
                },
            )
            self.readiness_checks()
        except Exception as exc:
            self.database.disconnect()
            metrics_registry.gauge(
                "action_control_plane_runtime_ready",
                "Whether the current runtime instance is ready to accept pilot traffic.",
            ).set(0)
            logger.exception(
                "runtime.startup.failed",
                extra={
                    "event": "runtime.startup.failed",
                    "service": self.settings.service_slug,
                    "environment": self.settings.environment,
                    "component": "runtime",
                    "startup_phase": startup_phase,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            raise

    def shutdown(self) -> None:
        self.database.disconnect()
        get_metrics_registry().gauge(
            "action_control_plane_runtime_ready",
            "Whether the current runtime instance is ready to accept pilot traffic.",
        ).set(0)
        logger.info(
            "runtime.shutdown.complete",
            extra={
                "event": "runtime.shutdown.complete",
                "service": self.settings.service_slug,
                "environment": self.settings.environment,
                "component": "runtime",
            },
        )

    def readiness_checks(self) -> dict[str, RuntimeCheckResult]:
        checks: dict[str, RuntimeCheckResult] = {
            "database": self._database_readiness(),
            "evidence_storage": self._evidence_storage_readiness(),
        }
        dependency_ready = get_metrics_registry().gauge(
            "action_control_plane_dependency_ready",
            "Dependency readiness status for runtime checks.",
            label_names=("check_name",),
        )
        all_ready = True
        for name, check in checks.items():
            is_ready = check.status == "ready"
            dependency_ready.set(1 if is_ready else 0, check_name=name)
            all_ready = all_ready and is_ready
        get_metrics_registry().gauge(
            "action_control_plane_runtime_ready",
            "Whether the current runtime instance is ready to accept pilot traffic.",
        ).set(1 if all_ready else 0)
        return checks

    def _database_readiness(self) -> RuntimeCheckResult:
        try:
            if self.database.healthcheck():
                return RuntimeCheckResult(
                    status="ready",
                    detail=f"{self.settings.database_backend()} connection ok",
                )
        except Exception as exc:
            return RuntimeCheckResult(
                status="not_ready",
                detail=f"database healthcheck failed: {exc.__class__.__name__}",
            )
        return RuntimeCheckResult(
            status="not_ready",
            detail="database healthcheck returned not ready",
        )

    def _evidence_storage_readiness(self) -> RuntimeCheckResult:
        try:
            evidence_storage_root = ensure_writable_directory(
                self.settings.evidence_storage_root,
                create=False,
            )
        except Exception as exc:
            return RuntimeCheckResult(
                status="not_ready",
                detail=f"evidence storage unavailable: {exc}",
            )
        return RuntimeCheckResult(
            status="ready",
            detail=f"writable directory available at {evidence_storage_root}",
        )
