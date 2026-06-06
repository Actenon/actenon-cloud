from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

DEFAULT_DEV_SIGNING_SECRET = "action-control-plane-dev-signing-secret"  # noqa: S105
DEFAULT_BOOTSTRAP_ADMIN_TOKEN = "action-control-plane-bootstrap-admin-token"  # noqa: S105


def ensure_writable_directory(path_value: str | Path, *, create: bool) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path

    if create:
        if path.exists() and not path.is_dir():
            raise ValueError(f"required path is not a directory: {path}")
        path.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        raise ValueError(f"required directory does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"required path is not a directory: {path}")

    probe_path = path / f".action-control-plane-probe-{uuid4().hex}"
    try:
        probe_path.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"required directory is not writable: {path}") from exc
    finally:
        try:
            probe_path.unlink(missing_ok=True)
        except OSError:
            pass

    return path


class Settings(BaseSettings):
    service_name: str = "Actenon Cloud"
    service_slug: str = "action-control-plane"
    version: str = "0.1.0"
    environment: Literal["local", "test", "staging", "production"] = "local"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    database_url: str = "sqlite+pysqlite:///./var/action_control_plane.db"
    evidence_upload_backend: Literal["filesystem", "object_store"] = "filesystem"
    evidence_storage_root: str = "./var/evidence"
    evidence_object_store_bucket: str | None = None
    evidence_object_store_prefix: str = "evidence"
    evidence_object_store_endpoint: str | None = None
    proof_issuer_name: str = "Actenon Cloud"
    proof_issuer_uri: str = "https://actenon-cloud.local/issuer"
    proof_issuer_trust_tier: str = "development_local"
    proof_default_ttl_seconds: int = Field(default=900, ge=60, le=604800)
    proof_max_ttl_seconds: int = Field(default=86400, ge=300, le=2592000)
    dev_signing_secret: str = DEFAULT_DEV_SIGNING_SECRET
    auth_mode: Literal[
        "development_signed_bearer", "external_managed_bearer"
    ] = "development_signed_bearer"
    bootstrap_admin_token: str = DEFAULT_BOOTSTRAP_ADMIN_TOKEN
    auth_operator_token_ttl_seconds: int = Field(default=3600, ge=300, le=604800)
    auth_service_token_ttl_seconds: int = Field(default=3600, ge=300, le=604800)
    capability_release_mode: Literal["development_simulated", "external_managed"] = (
        "development_simulated"
    )
    capability_default_ttl_seconds: int = Field(default=600, ge=60, le=604800)
    capability_max_ttl_seconds: int = Field(default=3600, ge=300, le=2592000)
    api_v1_prefix: str = "/api/v1"
    enable_docs: bool = True
    request_timeout_seconds: int = Field(default=30, ge=1, le=300)
    transparency_log_id: str = "actenon-transparency-log"
    transparency_log_identity_type: str = "service"
    transparency_log_display_name: str = "Actenon Transparency Log"
    issuer_status_authority_type: str = "service"
    issuer_status_authority_id: str = "actenon-issuer-registry"
    issuer_status_authority_display_name: str = "Actenon Issuer Registry"
    issuer_status_ttl_seconds: int = Field(default=300, ge=30, le=86400)
    issuer_status_max_staleness_seconds: int = Field(
        default=300,
        ge=30,
        le=86400,
    )

    model_config = SettingsConfigDict(
        env_prefix="ACTION_CONTROL_PLANE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("host must not be empty")
        return stripped

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_v1_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        if value != "/" and value.endswith("/"):
            raise ValueError("api_v1_prefix must not end with '/'")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        make_url(value)
        return value

    @field_validator("evidence_storage_root")
    @classmethod
    def validate_evidence_storage_root(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence_storage_root must not be empty")
        return value

    @field_validator("evidence_object_store_bucket", "evidence_object_store_endpoint")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("evidence_object_store_prefix")
    @classmethod
    def validate_evidence_object_store_prefix(cls, value: str) -> str:
        stripped = value.strip().strip("/")
        if not stripped:
            raise ValueError("evidence_object_store_prefix must not be empty")
        return stripped

    @field_validator(
        "proof_issuer_name",
        "proof_issuer_uri",
        "proof_issuer_trust_tier",
        "transparency_log_id",
        "transparency_log_identity_type",
        "transparency_log_display_name",
        "issuer_status_authority_type",
        "issuer_status_authority_id",
        "issuer_status_authority_display_name",
    )
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("dev_signing_secret", "bootstrap_admin_token")
    @classmethod
    def validate_secrets(cls, value: str) -> str:
        if len(value.strip()) < 16:
            raise ValueError("secret values must be at least 16 characters")
        return value

    @model_validator(mode="after")
    def validate_runtime_rules(self) -> Settings:
        url = make_url(self.database_url)
        if self.environment == "production" and url.get_backend_name() == "sqlite":
            raise ValueError("production requires a managed database backend, not sqlite")
        if self.environment == "production" and self.enable_docs:
            raise ValueError("production must disable interactive API docs")
        if self.proof_default_ttl_seconds > self.proof_max_ttl_seconds:
            raise ValueError("proof_default_ttl_seconds must not exceed proof_max_ttl_seconds")
        if self.capability_default_ttl_seconds > self.capability_max_ttl_seconds:
            raise ValueError(
                "capability_default_ttl_seconds must not exceed capability_max_ttl_seconds"
            )
        if (
            self.environment == "production"
            and self.dev_signing_secret == DEFAULT_DEV_SIGNING_SECRET
        ):
            raise ValueError("production must not use the default development signing secret")
        if self.environment == "production" and self.auth_mode == "development_signed_bearer":
            raise ValueError("production must not use development_signed_bearer auth mode")
        if (
            self.evidence_upload_backend == "object_store"
            and self.evidence_object_store_bucket is None
        ):
            raise ValueError(
                "object_store evidence upload backend requires evidence_object_store_bucket"
            )
        if (
            self.environment == "production"
            and self.bootstrap_admin_token == DEFAULT_BOOTSTRAP_ADMIN_TOKEN
        ):
            raise ValueError("production must not use the default bootstrap admin token")
        if (
            self.environment == "production"
            and self.capability_release_mode == "development_simulated"
        ):
            raise ValueError(
                "production must not use development_simulated capability release mode"
            )
        if self.auth_operator_token_ttl_seconds > 604800:
            raise ValueError("auth_operator_token_ttl_seconds exceeds the supported maximum")
        if self.auth_service_token_ttl_seconds > 604800:
            raise ValueError("auth_service_token_ttl_seconds exceeds the supported maximum")
        if self.issuer_status_ttl_seconds > self.issuer_status_max_staleness_seconds:
            raise ValueError(
                "issuer_status_ttl_seconds must not exceed "
                "issuer_status_max_staleness_seconds"
            )
        return self

    def validate_environment(self) -> None:
        try:
            self.model_validate(self.model_dump())
        except ValidationError as exc:
            raise ValueError("invalid runtime configuration") from exc
        ensure_writable_directory(self.evidence_storage_root, create=True)

    def database_backend(self) -> str:
        return make_url(self.database_url).get_backend_name()

    def resolved_evidence_storage_root(self) -> Path:
        return ensure_writable_directory(self.evidence_storage_root, create=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
