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
    )


def test_external_managed_bearer_stub_rejects_authentication(tmp_path: Path) -> None:
    session = create_session()
    try:
        service = AuthService(session, settings=make_settings(tmp_path))

        with pytest.raises(AuthenticationError, match="managed bearer integration is still a stub"):
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
