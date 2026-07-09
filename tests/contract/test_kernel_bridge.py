"""Phase 1 gate: cloud's export_kernel_pccb produces a real kernel PCCB.

This test proves cloud now builds real kernel PCCBs (not parallel
IssuedProof-as-dict) and that the PCCB verifies at the kernel's own verifier.
It also proves byte-identical canonicalization: the action-hash in cloud's
PCCB matches what the kernel's own build_action_hash_input produces.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.kernel_bridge import (
    export_kernel_pccb,
    pccb_action_hash,
    verify_kernel_pccb_at_edge,
)


@pytest.fixture(autouse=True)
def _stable_ed25519_key(monkeypatch, tmp_path):
    """Set up an Ed25519 key for all kernel bridge tests."""
    from app.services.ed25519_signer import generate_ed25519_keypair, save_ed25519_keypair
    key_path = tmp_path / "test-ed25519-key.json"
    kp = generate_ed25519_keypair(key_id="cloud-bridge-test-key")
    save_ed25519_keypair(kp, key_path)
    monkeypatch.setenv("ACTENON_ED25519_KEY_FILE", str(key_path))
    monkeypatch.delenv("ACTENON_SIGNING_KEY", raising=False)
    # Store on monkeypatch so tests can access it
    monkeypatch._ed25519_kp = kp


def _build_context_helper(*, tenant_id, actor_id, action_name,
                        action_capability, audience_id="actenon-cloud-gateway"):
    """Build a DynamicContextInput for kernel verification."""
    from actenon.models.contracts import AudienceRef
    from actenon.models.runtime import DynamicContextInput
    return DynamicContextInput(
        request_id="req-test",
        audience=AudienceRef(type="service", id=audience_id),
        scope_capabilities=(action_capability,),
        now=datetime.now(UTC),
    )


def _make_pccb(**overrides):
    defaults = {
        "tenant_id": "tenant-acme",
        "actor_id": "ops-alice",
        "action_name": "invoice.payment.refund",
        "action_capability": "invoice.payment.refund",
        "action_parameters": {"invoice_id": "inv-123", "amount": 2500, "currency": "USD"},
        "target_resource_type": "payment-provider",
        "target_resource_id": "stripe",
        "expires_at": datetime.now(UTC) + timedelta(minutes=15),
    }
    # Allow _make_pccb(amount=X) as a shortcut for overriding the amount param.
    if "amount" in overrides:
        amount = overrides.pop("amount")
        defaults["action_parameters"] = {**defaults["action_parameters"], "amount": amount}
    defaults.update(overrides)
    return export_kernel_pccb(**defaults)


def test_cloud_mints_real_kernel_pccb():
    """export_kernel_pccb returns a real kernel PCCB that verifies."""
    from actenon.proof.service import PCCBVerifier
    
    intent, pccb = _make_pccb()
    assert pccb.pccb_id.startswith("pccb_")
    assert pccb.signature.algorithm == "EdDSA", f"expected EdDSA, got {pccb.signature.algorithm}"
    assert pccb.action_hash.algorithm == "sha-256"

    # Verify with the kernel's own verifier
    import os
    from pathlib import Path

    from app.services.ed25519_signer import build_ed25519_signer, load_ed25519_keypair
    kp = load_ed25519_keypair(Path(os.environ["ACTENON_ED25519_KEY_FILE"]))
    signer = build_ed25519_signer(kp)
    verifier = PCCBVerifier(signer=signer)
    from actenon.models.contracts import AudienceRef
    from actenon.models.runtime import DynamicContextInput

    context = DynamicContextInput(
        request_id="req-test",
        audience=AudienceRef(type="service", id="actenon-cloud-gateway"),
        scope_capabilities=("invoice.payment.refund",),
        now=datetime.now(UTC),
    )
    verifier.verify(intent, pccb, context)  # raises on failure


def test_action_hash_uses_kernel_canonicalization():
    """The action-hash in cloud's PCCB equals the kernel's own hash."""
    from actenon.proof.canonical import sha256_hex
    from actenon.proof.service import build_action_hash_input

    intent, pccb = _make_pccb()
    expected = sha256_hex(build_action_hash_input(intent))
    assert pccb_action_hash(pccb) == expected


def test_mutation_detected_at_edge():
    """If the amount changes between issuance and execution, the edge refuses."""
    from actenon.core.errors import ProofVerificationError

    intent, pccb = _make_pccb(amount=2500)
    with pytest.raises(ProofVerificationError) as exc_info:
        verify_kernel_pccb_at_edge(
            intent,
            pccb,
            tenant_id="tenant-acme",
            actor_id="ops-alice",
            action_name="invoice.payment.refund",
            action_capability="invoice.payment.refund",
            action_parameters={  # mutated!
                "invoice_id": "inv-123", "amount": 999999, "currency": "USD",
            },
            target_resource_type="payment-provider",
            target_resource_id="stripe",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
    assert exc_info.value.refusal_code in ("ACTION_MISMATCH", "ACTION_HASH_MISMATCH")


def test_target_mutation_detected_at_edge():
    """Changing the target between issuance and execution is refused."""
    from actenon.core.errors import ProofVerificationError

    intent, pccb = _make_pccb()
    with pytest.raises(ProofVerificationError) as exc_info:
        verify_kernel_pccb_at_edge(
            intent,
            pccb,
            tenant_id="tenant-acme",
            actor_id="ops-alice",
            action_name="invoice.payment.refund",
            action_capability="invoice.payment.refund",
            action_parameters={"invoice_id": "inv-123", "amount": 2500, "currency": "USD"},
            target_resource_type="payment-provider",
            target_resource_id="different-provider",  # mutated!
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
    assert exc_info.value.refusal_code == "TARGET_MISMATCH"


def test_cross_signer_rejected():
    """A PCCB minted with key A is rejected by key B's verifier."""
    from actenon.core.errors import ProofVerificationError
    from actenon.proof.service import PCCBVerifier

    from app.services.ed25519_signer import build_ed25519_signer, generate_ed25519_keypair

    intent, pccb = _make_pccb()

    # Verify with a DIFFERENT Ed25519 keypair
    wrong_kp = generate_ed25519_keypair(key_id="wrong-key")
    wrong_signer = build_ed25519_signer(wrong_kp)
    wrong_verifier = PCCBVerifier(signer=wrong_signer)

    # _build_context_helper is defined below in this file

    context = _build_context_helper(
        tenant_id="tenant-acme",
        actor_id="ops-alice",
        action_name="invoice.payment.refund",
        action_capability="invoice.payment.refund",
        audience_id="actenon-cloud-gateway",
    )
    with pytest.raises(ProofVerificationError) as exc_info:
        wrong_verifier.verify(intent, pccb, context)
    assert exc_info.value.refusal_code == "SIGNATURE_INVALID"
