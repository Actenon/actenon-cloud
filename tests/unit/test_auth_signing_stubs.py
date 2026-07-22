from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.config import Settings
from app.database import Base
from app.services.auth import AuthenticationError, AuthService, AuthValidationError


def create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return Session(bind=engine)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="staging",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'stub.db'}",
        evidence_storage_root=str(tmp_path / "evidence"),
        enable_docs=False,
        auth_mode="external_managed_bearer",
        kms_endpoint="https://kms.test.example.com",
        capability_release_mode="external_managed",
        dev_signing_secret="test-secret-at-least-16-chars",  # noqa: S106
        bootstrap_admin_token="test-bootstrap-token-16-chars",  # noqa: S106
    )


def test_external_managed_bearer_stub_rejects_authentication(tmp_path: Path) -> None:
    session = create_session()
    try:
        service = AuthService(session, settings=make_settings(tmp_path))

        # B6: external_managed_bearer now routes through the OIDC verifier.
        # Without oidc_issuer_url configured, authentication is refused before
        # any JWKS fetch is attempted.
        with pytest.raises(
            AuthenticationError,
            match="OIDC token verification requires oidc_issuer_url",
        ):
            service.authenticate_bearer_token("stub-token")
    finally:
        session.close()


def test_external_managed_bearer_stub_disables_local_bootstrap(tmp_path: Path) -> None:
    session = create_session()
    try:
        service = AuthService(session, settings=make_settings(tmp_path))

        with pytest.raises(
            AuthValidationError,
            match="development token issuance endpoints are unavailable",
        ):
            service.bootstrap_platform_admin(
                bootstrap_token="x" * 32,
                email="admin@example.com",
                display_name="Admin",
            )
    finally:
        session.close()
