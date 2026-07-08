"""Phase 4 test: cloud's export_kernel_pccb uses Ed25519 when a key is available.

Proves cloud's kernel_bridge now prefers Ed25519 over HMAC, matching permit's
Phase 4 hardening. The PCCB must be EdDSA-signed, not HS256.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.ed25519_signer import (
    generate_ed25519_keypair,
    save_ed25519_keypair,
)
from app.services.kernel_bridge import export_kernel_pccb


@pytest.fixture
def ed25519_keyfile(tmp_path, monkeypatch):
    """Generate an Ed25519 keypair, point the env at it."""
    key_path = tmp_path / "cloud-ed25519-key.json"
    kp = generate_ed25519_keypair(key_id="cloud-test-key")
    save_ed25519_keypair(kp, key_path)
    monkeypatch.setenv("ACTENON_ED25519_KEY_FILE", str(key_path))
    monkeypatch.delenv("ACTENON_SIGNING_KEY", raising=False)
    yield key_path, kp


def test_cloud_mints_ed25519_signed_pccb(ed25519_keyfile):
    """When an Ed25519 key is available, cloud's PCCBs are EdDSA-signed."""
    _, kp = ed25519_keyfile
    intent, pccb = export_kernel_pccb(
        tenant_id="tenant-test",
        actor_id="actor-test",
        action_name="invoice.payment.refund",
        action_capability="invoice.payment.refund",
        action_parameters={"invoice_id": "inv-1", "amount": 100, "currency": "USD"},
        target_resource_type="payment-provider",
        target_resource_id="stripe",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    assert pccb.signature.algorithm == "EdDSA", (
        f"expected EdDSA, got {pccb.signature.algorithm}"
    )
    assert pccb.signature.key_id == kp.key_id


def test_cloud_ed25519_pccb_verifies_with_correct_key(ed25519_keyfile):
    """Cloud's Ed25519-signed PCCB verifies with the correct keypair."""
    from actenon.models.contracts import AudienceRef
    from actenon.models.runtime import DynamicContextInput
    from actenon.proof.service import PCCBVerifier

    from app.services.ed25519_signer import build_ed25519_signer

    _, kp = ed25519_keyfile
    intent, pccb = export_kernel_pccb(
        tenant_id="tenant-test",
        actor_id="actor-test",
        action_name="invoice.payment.refund",
        action_capability="invoice.payment.refund",
        action_parameters={"invoice_id": "inv-1", "amount": 100, "currency": "USD"},
        target_resource_type="payment-provider",
        target_resource_id="stripe",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    signer = build_ed25519_signer(kp)
    verifier = PCCBVerifier(signer=signer)
    context = DynamicContextInput(
        request_id="req-test",
        audience=AudienceRef(type="service", id="actenon-cloud-gateway"),
        scope_capabilities=("invoice.payment.refund",),
        now=datetime.now(UTC),
    )
    verifier.verify(intent, pccb, context)


def test_cloud_ed25519_pccb_rejected_by_wrong_key(ed25519_keyfile):
    """Cloud's Ed25519-signed PCCB is rejected by a different keypair."""
    from actenon.core.errors import ProofVerificationError
    from actenon.models.contracts import AudienceRef
    from actenon.models.runtime import DynamicContextInput
    from actenon.proof.service import PCCBVerifier

    from app.services.ed25519_signer import build_ed25519_signer

    _, _ = ed25519_keyfile
    intent, pccb = export_kernel_pccb(
        tenant_id="tenant-test",
        actor_id="actor-test",
        action_name="invoice.payment.refund",
        action_capability="invoice.payment.refund",
        action_parameters={"invoice_id": "inv-1", "amount": 100, "currency": "USD"},
        target_resource_type="payment-provider",
        target_resource_id="stripe",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    wrong_kp = generate_ed25519_keypair()
    wrong_signer = build_ed25519_signer(wrong_kp)
    wrong_verifier = PCCBVerifier(signer=wrong_signer)
    context = DynamicContextInput(
        request_id="req-test",
        audience=AudienceRef(type="service", id="actenon-cloud-gateway"),
        scope_capabilities=("invoice.payment.refund",),
        now=datetime.now(UTC),
    )
    with pytest.raises(ProofVerificationError) as exc_info:
        wrong_verifier.verify(intent, pccb, context)
    assert exc_info.value.refusal_code == "SIGNATURE_INVALID"
