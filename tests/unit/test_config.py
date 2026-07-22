from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_local_runtime_accepts_sqlite(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'local.db'}",
        evidence_storage_root=str(tmp_path / "evidence"),
    )

    assert settings.environment == "local"
    assert settings.database_url.endswith("local.db")
    settings.validate_environment()
    assert (tmp_path / "evidence").exists()


def test_validate_environment_rejects_file_backed_evidence_root(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence.txt"
    evidence_file.write_text("not-a-directory", encoding="utf-8")
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'local.db'}",
        evidence_storage_root=str(evidence_file),
    )

    with pytest.raises(ValueError, match="required path is not a directory"):
        settings.validate_environment()


def test_object_store_upload_backend_requires_bucket(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url=f"sqlite+pysqlite:///{tmp_path / 'local.db'}",
            evidence_storage_root=str(tmp_path / "evidence"),
            evidence_upload_backend="object_store",
        )


def test_object_store_upload_backend_accepts_explicit_bucket(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'local.db'}",
        evidence_storage_root=str(tmp_path / "evidence"),
        evidence_upload_backend="object_store",
        evidence_object_store_bucket="pilot-evidence",
        evidence_object_store_prefix="invoice-payment/evidence",
        evidence_object_store_endpoint="https://object-storage.example",
    )

    assert settings.evidence_upload_backend == "object_store"
    assert settings.evidence_object_store_bucket == "pilot-evidence"


def test_production_runtime_rejects_sqlite() -> None:
    nondefault_secret = "x" * 32
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="sqlite+pysqlite:///./var/production.db",
            enable_docs=False,
            dev_signing_secret=nondefault_secret,
        )


def test_production_runtime_rejects_docs() -> None:
    nondefault_secret = "x" * 32
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example/control_plane",
            enable_docs=True,
            dev_signing_secret=nondefault_secret,
        )


def test_production_runtime_rejects_default_dev_signing_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example/control_plane",
            enable_docs=False,
        )


def test_production_runtime_rejects_development_auth_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example/control_plane",
            enable_docs=False,
            dev_signing_secret="x" * 32,
            bootstrap_admin_token="y" * 32,
            auth_mode="development_signed_bearer",
        )


def test_production_runtime_accepts_external_managed_auth_stub() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://user:pass@db.example/control_plane",
        enable_docs=False,
        dev_signing_secret="x" * 32,
        bootstrap_admin_token="y" * 32,
        auth_mode="external_managed_bearer",
        capability_release_mode="external_managed",
        kms_endpoint="https://kms.example.com",
        oidc_issuer_url="https://auth.example.com/realms/cloud",
        oidc_client_id="actenon-cloud",
        oidc_client_secret="oidc-secret-value",  # noqa: S106
    )

    assert settings.auth_mode == "external_managed_bearer"
    assert settings.oidc_issuer_url == "https://auth.example.com/realms/cloud"


def test_production_runtime_rejects_default_bootstrap_admin_token() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example/control_plane",
            enable_docs=False,
            dev_signing_secret="x" * 32,
        )


def test_production_runtime_rejects_development_capability_release_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db.example/control_plane",
            enable_docs=False,
            dev_signing_secret="x" * 32,
            bootstrap_admin_token="y" * 32,
            capability_release_mode="development_simulated",
        )
