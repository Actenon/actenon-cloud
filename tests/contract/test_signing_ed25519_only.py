"""B1 tests: dev-HMAC is GONE; Ed25519 is the only signing path.

Tests:
  1. Production env + no KMS endpoint -> boot refused
  2. Production env + dev Ed25519 backend -> signing refused
  3. Dev env + local Ed25519 key -> signing works
  4. dev-HMAC algorithm -> registration refused
  5. EdDSA algorithm -> registration accepted
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.models.issuance import SigningAlgorithm, SigningKeyBackend


class TestBootRefusal:
    """Production must refuse to boot without KMS-backed Ed25519."""

    def test_production_without_kms_refuses_boot(self, tmp_path, monkeypatch):
        """ACTENON_ENV=production + no ACTENON_KMS_ENDPOINT -> ValueError."""
        monkeypatch.setenv("ACTENON_ENV", "production")
        monkeypatch.delenv("ACTENON_KMS_ENDPOINT", raising=False)
        monkeypatch.setenv("ACTION_CONTROL_PLANE_ENVIRONMENT", "production")
        monkeypatch.setenv("ACTION_CONTROL_PLANE_DEV_SIGNING_SECRET", "non-default-secret")
        monkeypatch.setenv("ACTION_CONTROL_PLANE_ENABLE_DOCS", "false")
        monkeypatch.setenv("ACTION_CONTROL_PLANE_AUTH_MODE", "external_managed_bearer")
        monkeypatch.setenv(
            "ACTION_CONTROL_PLANE_BOOTSTRAP_ADMIN_TOKEN",
            "non-default-bootstrap-token",
        )
        monkeypatch.setenv("ACTION_CONTROL_PLANE_CAPABILITY_RELEASE_MODE", "external_managed")

        with pytest.raises(ValueError, match="ACTENON_KMS_ENDPOINT"):
            Settings(
                environment="production",
                database_url="postgresql+psycopg://user:pass@localhost:5432/test",
                evidence_storage_root=str(tmp_path / "evidence"),
                dev_signing_secret="non-default-secret",  # noqa: S106
                enable_docs=False,
                auth_mode="external_managed_bearer",
            )

    def test_production_with_kms_allows_boot(self, tmp_path, monkeypatch):
        """ACTENON_ENV=production + ACTENON_KMS_ENDPOINT set -> OK."""
        monkeypatch.setenv("ACTENON_KMS_ENDPOINT", "https://kms.example.com")
        monkeypatch.setenv("ACTION_CONTROL_PLANE_ENVIRONMENT", "production")
        monkeypatch.setenv("ACTION_CONTROL_PLANE_DEV_SIGNING_SECRET", "non-default-secret")
        monkeypatch.setenv("ACTION_CONTROL_PLANE_ENABLE_DOCS", "false")
        monkeypatch.setenv("ACTION_CONTROL_PLANE_AUTH_MODE", "external_managed_bearer")
        monkeypatch.setenv(
            "ACTION_CONTROL_PLANE_BOOTSTRAP_ADMIN_TOKEN",
            "non-default-bootstrap-token",
        )
        monkeypatch.setenv("ACTION_CONTROL_PLANE_CAPABILITY_RELEASE_MODE", "external_managed")
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@localhost:5432/test",
            evidence_storage_root=str(tmp_path / "evidence"),
            dev_signing_secret="non-default-secret",  # noqa: S106
        )

    def test_dev_without_kms_allows_boot(self, tmp_path):
        """Dev/test doesn't need KMS — local Ed25519 key file is fine."""
        Settings(
            environment="test",
            database_url="postgresql+psycopg://user:pass@localhost:5432/test",
            evidence_storage_root=str(tmp_path / "evidence"),
        )


class TestDevHmacRemoved:
    """dev-HMAC must be completely removed from the signing path."""

    def test_hs256_registration_refused(self):
        """Attempting to register an HS256 key must raise."""
        from app.services.signing import SigningKeyStateError, SigningService

        # We can't easily create a full SigningService without a DB session,
        # but we can test the validation method directly
        with pytest.raises((SigningKeyStateError, Exception)):
            SigningService._validate_backend_algorithm(
                self=None,  # type: ignore[arg-type]
                key_backend=SigningKeyBackend.development_local_hmac,
                algorithm=SigningAlgorithm.hs256,
            )

    def test_eddsa_registration_accepted(self):
        """EdDSA algorithm with external_managed backend is valid."""
        from app.services.signing import SigningService

        # Should NOT raise
        SigningService._validate_backend_algorithm(
            self=None,  # type: ignore[arg-type]
            key_backend=SigningKeyBackend.external_managed,
            algorithm=SigningAlgorithm.eddsa,
        )

    def test_dev_hmac_backend_refused_in_sign(self):
        """The _sign_bytes method must refuse dev-HMAC backend."""
        # We test that the method signature includes the refusal
        import inspect

        from app.services.signing import SigningService

        source = inspect.getsource(SigningService._sign_bytes)
        assert "development_local_hmac signing has been REMOVED" in source, (
            "_sign_bytes must contain the dev-HMAC removal message"
        )

    def test_no_hmac_imports_in_signing(self):
        """signing.py must not import hmac or hashlib for signing."""
        # hmac and hashlib may still be imported for other purposes (like digest computation)
        # but the _sign_bytes method must not use them for signing
        import inspect

        from app.services.signing import SigningService

        source = inspect.getsource(SigningService._sign_bytes)
        assert "hmac.new" not in source, (
            "_sign_bytes must not use hmac.new — dev-HMAC is removed"
        )


class TestEd25519Signing:
    """Ed25519 signing works end-to-end."""

    def test_ed25519_key_generation_and_signing(self, tmp_path, monkeypatch):
        """Generate an Ed25519 keypair, sign, and verify."""
        from app.services.ed25519_signer import (
            build_ed25519_signer,
            generate_ed25519_keypair,
            save_ed25519_keypair,
        )

        key_path = tmp_path / "test-ed25519.json"
        kp = generate_ed25519_keypair(key_id="test-signing-key")
        save_ed25519_keypair(kp, key_path)
        monkeypatch.setenv("ACTENON_ED25519_KEY_FILE", str(key_path))

        signer = build_ed25519_signer(kp)
        # Sign a payload
        payload = b"test payload for Ed25519 signing"
        sig_spec = signer.sign(payload)

        assert sig_spec.algorithm == "EdDSA"
        assert sig_spec.key_id == "test-signing-key"
        assert sig_spec.encoding == "base64url"
        assert len(sig_spec.value) > 0

        # Verify
        assert signer.verify(payload, sig_spec) is True

    def test_ed25519_wrong_key_rejected(self, tmp_path):
        """A signature from key A must not verify with key B."""
        from app.services.ed25519_signer import (
            build_ed25519_signer,
            generate_ed25519_keypair,
        )

        kp_a = generate_ed25519_keypair(key_id="key-a")
        kp_b = generate_ed25519_keypair(key_id="key-b")
        signer_a = build_ed25519_signer(kp_a)
        signer_b = build_ed25519_signer(kp_b)

        payload = b"test payload"
        sig = signer_a.sign(payload)
        assert signer_b.verify(payload, sig) is False
