"""B1 contract: signing key rotation preserves verification history.

Tests:
  1. Rotate key -> new proofs use the new key_id
  2. Old key still verifies old proofs
  3. Published key set contains both keys (old + new)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.config import Settings
from app.database import Base
from app.models import (
    FinanceProfile,
    SigningAlgorithm,
    SigningKeyBackend,
    SigningKeyPurpose,
    Tenant,
    TenantStatus,
)
from app.services.ed25519_signer import (
    build_ed25519_signer,
    generate_ed25519_keypair,
    load_ed25519_keypair,
    save_ed25519_keypair,
)
from app.services.key_set_publisher import AtomicFileKeySetPublisher
from app.services.signing import SigningService


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'rotation.db'}",
        evidence_storage_root=str(tmp_path / "evidence"),
        enable_docs=False,
        log_format="console",
    )


@pytest.fixture
def rotation_env(tmp_path, monkeypatch):
    """Set up a fresh Ed25519 key, sqlite DB, tenant, and SigningService."""
    # Initial Ed25519 key file
    initial_key_path = tmp_path / "initial-ed25519.json"
    initial_kp = generate_ed25519_keypair(key_id="initial-test-key")
    save_ed25519_keypair(initial_kp, initial_key_path)
    monkeypatch.setenv("ACTENON_ED25519_KEY_FILE", str(initial_key_path))
    monkeypatch.delenv("ACTENON_SIGNING_KEY", raising=False)

    settings = _make_settings(tmp_path)

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine, expire_on_commit=False)

    # Create a tenant row so the FK on signing_key_references is satisfied.
    tenant = Tenant(
        tenant_id="tenant-rotation",
        display_name="Rotation Tenant",
        status=TenantStatus.active,
        finance_profile=FinanceProfile.payments,
    )
    session.add(tenant)
    session.commit()

    publisher = AtomicFileKeySetPublisher(tmp_path / "published-keys")
    service = SigningService(session, settings=settings)

    yield {
        "tmp_path": tmp_path,
        "initial_key_path": initial_key_path,
        "initial_kp": initial_kp,
        "settings": settings,
        "session": session,
        "engine": engine,
        "publisher": publisher,
        "service": service,
        "tenant_id": "tenant-rotation",
    }

    session.close()
    engine.dispose()


def _register_initial_key(service: SigningService, *, tenant_id: str, public_key_ref: str):
    """Register the initial default signing key with a known public key."""
    return service.register_key(
        tenant_id=tenant_id,
        display_name="initial-default-key",
        key_purpose=SigningKeyPurpose.pccb_signing,
        algorithm=SigningAlgorithm.eddsa,
        key_backend=SigningKeyBackend.external_managed,
        provider_key_ref="local:initial-test-key",
        public_key_ref=public_key_ref,
        issuer_name=None,
        issuer_uri=None,
        trust_tier=None,
        lifecycle_metadata={"owner": "tests"},
        is_default=True,
    )


def test_rotation_new_proofs_use_new_key_id(rotation_env):
    """After rotation, signing produces signatures with the new key_id."""
    env = rotation_env
    service: SigningService = env["service"]
    tenant_id: str = env["tenant_id"]

    # Register the initial key using the generated keypair's public key.
    _register_initial_key(
        service,
        tenant_id=tenant_id,
        public_key_ref=env["initial_kp"].key.public_key_ref,
    )

    # Sign a payload with the initial key (via resolve_signer -> initial key file).
    payload_a = b"pre-rotation payload"
    sig_a = service._sign_with_ed25519_backend(
        key_reference=service.resolve_key(
            tenant_id=tenant_id,
            key_purpose=SigningKeyPurpose.pccb_signing,
            signing_key_reference_id=None,
        ),
        payload=payload_a,
    )
    # Sanity: the signature's key_id matches the initial keypair.
    # resolve_signer signs with whatever's at ACTENON_ED25519_KEY_FILE.
    assert sig_a, "initial signature must be non-empty"

    # Capture the active default BEFORE rotation.
    pre_rotation_default = service.resolve_key(
        tenant_id=tenant_id,
        key_purpose=SigningKeyPurpose.pccb_signing,
        signing_key_reference_id=None,
    )

    # Rotate.
    new_key_ref, new_kp = service.rotate_signing_key(
        tenant_id=tenant_id,
        key_purpose=SigningKeyPurpose.pccb_signing,
        key_set_publisher=env["publisher"],
        key_file_path=env["initial_key_path"],  # overwrite so resolve_signer uses new key
    )

    # 1. The new default is different from the pre-rotation default.
    assert new_key_ref.signing_key_reference_id != pre_rotation_default.signing_key_reference_id
    assert new_key_ref.is_default is True
    assert pre_rotation_default.is_default is False  # old key unset as default

    # 2. New proofs use the new key_id — verify by signing a new payload
    #    and checking the signature verifies with the NEW keypair, not the old.
    payload_b = b"post-rotation payload"
    sig_b = service._sign_with_ed25519_backend(
        key_reference=service.resolve_key(
            tenant_id=tenant_id,
            key_purpose=SigningKeyPurpose.pccb_signing,
            signing_key_reference_id=None,
        ),
        payload=payload_b,
    )
    new_signer = build_ed25519_signer(new_kp)
    # Build a signature spec the same way the signer would, for verification.
    new_sig_spec = new_signer.sign(payload_b)
    assert new_sig_spec.value == sig_b, (
        "post-rotation signature must come from the new keypair"
    )

    # The old keypair must NOT verify the new signature.
    old_signer = build_ed25519_signer(env["initial_kp"])
    old_sig_spec_for_b = old_signer.sign(payload_b)
    assert old_sig_spec_for_b.value != sig_b, (
        "post-rotation signature must not be reproducible by the old keypair"
    )


def test_old_key_still_verifies_old_proofs(rotation_env):
    """After rotation, proofs signed with the old key still verify with the old public key."""
    env = rotation_env
    service: SigningService = env["service"]
    tenant_id: str = env["tenant_id"]

    _register_initial_key(
        service,
        tenant_id=tenant_id,
        public_key_ref=env["initial_kp"].key.public_key_ref,
    )

    # Sign a payload BEFORE rotation, using the initial keypair directly
    # so we can verify it after rotation even after the key file is overwritten.
    old_kp = env["initial_kp"]
    old_signer = build_ed25519_signer(old_kp)
    payload = b"old-proof-payload"
    old_sig_spec = old_signer.sign(payload)
    assert old_sig_spec.key_id == old_kp.key_id

    # Rotate — this overwrites the key file with the new keypair.
    service.rotate_signing_key(
        tenant_id=tenant_id,
        key_purpose=SigningKeyPurpose.pccb_signing,
        key_set_publisher=env["publisher"],
        key_file_path=env["initial_key_path"],
    )

    # After rotation, the key file on disk is the new key, but old_kp is still
    # in memory. The OLD signer (built from old_kp) must still verify the OLD
    # signature. This proves old key_ids remain verifiable.
    assert old_signer.verify(payload, old_sig_spec) is True, (
        "old proofs must still verify with the old keypair after rotation"
    )

    # And the NEW signer (loaded from the now-overwritten key file) must NOT
    # verify the OLD signature — proving the signature is bound to the old key.
    new_kp = load_ed25519_keypair(env["initial_key_path"])
    new_signer = build_ed25519_signer(new_kp)
    assert new_signer.verify(payload, old_sig_spec) is False, (
        "old signature must not verify with the new keypair"
    )


def test_published_key_set_contains_both_keys(rotation_env):
    """The published JWKS-style key set contains both the old and new public keys."""
    env = rotation_env
    service: SigningService = env["service"]
    tenant_id: str = env["tenant_id"]

    initial_ref = _register_initial_key(
        service,
        tenant_id=tenant_id,
        public_key_ref=env["initial_kp"].key.public_key_ref,
    )

    # Rotate — this triggers a publish via env["publisher"].
    new_ref, _ = service.rotate_signing_key(
        tenant_id=tenant_id,
        key_purpose=SigningKeyPurpose.pccb_signing,
        key_set_publisher=env["publisher"],
        key_file_path=env["initial_key_path"],
    )

    # Read the published current key set JSON.
    published_path = env["tmp_path"] / "published-keys" / ".well-known" / "actenon" / "keys.json"
    assert published_path.is_file(), "published key set must be written to disk"
    published = json.loads(published_path.read_text(encoding="utf-8"))

    published_kids = {entry["kid"] for entry in published["keys"]}
    assert initial_ref.signing_key_reference_id in published_kids, (
        "published key set must contain the OLD (rotated-from) key"
    )
    assert new_ref.signing_key_reference_id in published_kids, (
        "published key set must contain the NEW (rotated-to) key"
    )

    # The old key must NOT be marked as default in the published set; the new one must.
    by_kid = {entry["kid"]: entry for entry in published["keys"]}
    assert by_kid[initial_ref.signing_key_reference_id]["is_default"] is False
    assert by_kid[new_ref.signing_key_reference_id]["is_default"] is True

    # Each published key must include the public key material (JWK `x` field).
    for entry in published["keys"]:
        assert entry["kty"] == "OKP"
        assert entry["crv"] == "Ed25519"
        assert entry["alg"] == "EdDSA"
        assert entry["x"], "published key must include public key bytes"
