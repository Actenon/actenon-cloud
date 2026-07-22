"""B6 contract tests: bootstrap-admin / dev-bearer backdoor is removed in
production; OIDC token verification is the production identity path.

Tests:
  1. Production env + dev auth mode -> boot refused (existing guard, verified
     to still pass after the B6 changes).
  2. Production env + OIDC configured -> boot OK.
  3. OIDC token verification interface exists on AuthService.
  4. Dev signed-bearer path refuses authentication in production even when
     the config validator is bypassed (defense in depth).
  5. OIDC verifier refuses tokens when oidc_issuer_url is not configured.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.config import Settings
from app.database import Base
from app.services.auth import (
    AuthenticationError,
    AuthService,
    _verify_oidc_jwt,
    reset_oidc_jwks_cache,
)


def _production_kwargs(tmp_path: Path) -> dict[str, object]:
    """Common kwargs that satisfy every production guard except OIDC."""
    return {
        "environment": "production",
        "database_url": "postgresql+psycopg://user:pass@db.example/control_plane",
        "evidence_storage_root": str(tmp_path / "evidence"),
        "enable_docs": False,
        "dev_signing_secret": "non-default-secret-32-chars",  # noqa: S106
        "bootstrap_admin_token": "non-default-bootstrap-token-32",  # noqa: S106
        "auth_mode": "external_managed_bearer",
        "capability_release_mode": "external_managed",
        "kms_endpoint": "https://kms.example.com",
    }


class TestProductionBootRefusal:
    """Production must refuse to boot with the dev-bearer backdoor."""

    def test_production_env_with_dev_auth_refuses_boot(self, tmp_path: Path) -> None:
        """The existing production+dev_auth guard (test_config.py) still passes."""
        with pytest.raises(ValidationError):
            Settings(
                environment="production",
                database_url="postgresql+psycopg://user:pass@db.example/control_plane",
                enable_docs=False,
                dev_signing_secret="x" * 32,
                bootstrap_admin_token="y" * 32,
                auth_mode="development_signed_bearer",
            )

    def test_production_env_without_oidc_refuses_boot(self, tmp_path: Path) -> None:
        """B6: production without oidc_issuer_url must refuse to boot."""
        kwargs = _production_kwargs(tmp_path)
        # oidc_issuer_url is left at the default ("")
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            Settings(**kwargs)
        message = str(exc_info.value)
        assert "oidc_issuer_url" in message, (
            f"production boot without OIDC must mention oidc_issuer_url; got: {message}"
        )


class TestProductionBootWithOidc:
    """Production env + OIDC configured -> boot OK."""

    def test_production_env_with_oidc_boots(self, tmp_path: Path) -> None:
        kwargs = _production_kwargs(tmp_path)
        kwargs.update(
            oidc_issuer_url="https://auth.example.com/realms/cloud",
            oidc_client_id="actenon-cloud",
            oidc_client_secret="oidc-client-secret-value",  # noqa: S106
        )
        settings = Settings(**kwargs)
        assert settings.environment == "production"
        assert settings.oidc_issuer_url == "https://auth.example.com/realms/cloud"
        assert settings.oidc_client_id == "actenon-cloud"

    def test_production_env_with_empty_oidc_client_id_still_boots(
        self, tmp_path: Path
    ) -> None:
        """oidc_client_id is optional at boot (audience check is per-request)."""
        kwargs = _production_kwargs(tmp_path)
        kwargs.update(
            oidc_issuer_url="https://auth.example.com/realms/cloud",
        )
        settings = Settings(**kwargs)
        assert settings.oidc_issuer_url == "https://auth.example.com/realms/cloud"


class TestOidcVerificationInterface:
    """The OIDC token verification interface exists on AuthService."""

    def test_auth_service_exposes_verify_oidc_token_method(self, tmp_path: Path) -> None:
        """AuthService has a callable verify_oidc_token method."""
        assert hasattr(AuthService, "verify_oidc_token"), (
            "AuthService must expose a verify_oidc_token method for OIDC verification"
        )
        assert callable(AuthService.verify_oidc_token)

    def test_verify_oidc_token_refuses_without_issuer_config(self, tmp_path: Path) -> None:
        """When oidc_issuer_url is empty, verify_oidc_token refuses early."""
        engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=engine)
        session = Session(bind=engine)
        try:
            settings = Settings(
                environment="test",
                database_url=f"sqlite+pysqlite:///{tmp_path / 'oidc.db'}",
                evidence_storage_root=str(tmp_path / "evidence"),
                enable_docs=False,
            )
            service = AuthService(session, settings=settings)
            with pytest.raises(AuthenticationError, match="oidc_issuer_url"):
                service.verify_oidc_token("not.a.jwt")
        finally:
            session.close()

    def test_module_level_verify_oidc_jwt_helper_exists(self) -> None:
        """A module-level _verify_oidc_jwt helper backs the method."""
        assert callable(_verify_oidc_jwt)

    def test_module_level_jwks_cache_reset_is_callable(self) -> None:
        """The JWKS cache reset hook is callable (for tests / operations)."""
        # Should not raise.
        reset_oidc_jwks_cache()


class TestDevBearerRefusedInProduction:
    """The dev signed-bearer path must refuse authentication in production."""

    def test_authenticate_bearer_token_refuses_dev_bearer_in_production(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Defense in depth: even if the config validator is bypassed, the
        AuthService.authenticate_bearer_token path refuses dev-bearer tokens
        in production.
        """
        # Construct production settings with dev auth mode by bypassing the
        # model validator (this is what "defense in depth" tests — the runtime
        # guard must catch what the config guard missed).
        # We construct via model_construct to skip validation, then patch the
        # environment/auth_mode to simulate a misconfigured production boot.
        engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=engine)
        session = Session(bind=engine)
        try:
            settings = Settings(
                environment="test",
                database_url=f"sqlite+pysqlite:///{tmp_path / 'prod-bypass.db'}",
                evidence_storage_root=str(tmp_path / "evidence"),
                enable_docs=False,
            )
            # Simulate a production misconfiguration where dev_signed_bearer
            # is somehow active. The runtime guard in authenticate_bearer_token
            # must refuse this regardless of the config validator.
            object.__setattr__(settings, "environment", "production")
            object.__setattr__(settings, "auth_mode", "development_signed_bearer")

            service = AuthService(session, settings=settings)
            with pytest.raises(
                AuthenticationError,
                match="development signed bearer authentication is refused in production",
            ):
                service.authenticate_bearer_token("acp1.eyJ2IjoxfQ.signature")
        finally:
            session.close()
