"""B2 tests: PHI-shaped params never appear in the immutable hash-chained record.

Tests:
  1. PHI-shaped params (patient_name, ssn, diagnosis, note) are committed,
     not stored in plaintext in the committed_params.
  2. Erasing the evidence blob leaves the commitment intact.
  3. The commitment still proves the params matched (given the params,
     recompute + compare).
  4. Safe fields (amount, currency, invoice_number) are kept in plaintext.
"""

from __future__ import annotations

from app.services.field_classification import (
    classify_params,
    verify_commitment,
)

TENANT_SALT = "tenant-acme-salt-12345"


def test_phi_fields_are_committed_not_plaintext():
    """PHI-shaped params must be replaced with commitments, not stored raw."""
    params = {
        "patient_name": "John Doe",
        "ssn": "123-45-6789",
        "diagnosis": "Type 2 Diabetes",
        "note": "Patient reports chest pain after exercise. Follow up in 2 weeks.",
        "amount_minor": 12500,
        "currency": "USD",
        "invoice_number": "INV-001",
    }

    committed, raw = classify_params(params, tenant_salt=TENANT_SALT)

    # Sensitive fields must NOT appear as plaintext in committed
    assert committed["patient_name"] != "John Doe", "patient_name must be committed"
    assert committed["ssn"] != "123-45-6789", "ssn must be committed"
    assert committed["diagnosis"] != "Type 2 Diabetes", "diagnosis must be committed"
    assert committed["note"] != params["note"], "note must be committed"

    # They must be commitments (dicts with _commitment key)
    assert "_commitment" in committed["patient_name"]
    assert "_commitment" in committed["ssn"]
    assert "_commitment" in committed["diagnosis"]
    assert "_commitment" in committed["note"]

    # Safe fields ARE in plaintext
    assert committed["amount_minor"] == 12500
    assert committed["currency"] == "USD"
    assert committed["invoice_number"] == "INV-001"

    # Raw values are in the evidence dict, keyed by commitment
    assert len(raw) == 4  # 4 sensitive fields
    assert "John Doe" in raw.values()
    assert "123-45-6789" in raw.values()


def test_erasing_evidence_preserves_commitment():
    """Erasing the raw evidence leaves the commitment intact — GDPR Art.17."""
    params = {
        "patient_name": "Jane Smith",
        "ssn": "987-65-4321",
        "amount_minor": 5000,
    }

    committed, raw = classify_params(params, tenant_salt=TENANT_SALT)

    # Simulate GDPR erasure: delete the raw evidence
    raw.clear()

    # The committed params are still valid (commitments are self-contained)
    assert "_commitment" in committed["patient_name"]
    assert "_commitment" in committed["ssn"]
    assert committed["amount_minor"] == 5000

    # The hash chain would still verify because it hashes the committed params,
    # not the raw evidence.


def test_commitment_proves_params_matched():
    """Given the original params, recompute the commitment and verify it matches."""
    params = {
        "patient_name": "Alice Johnson",
        "diagnosis": "Hypertension",
        "amount_minor": 10000,
    }

    committed, _ = classify_params(params, tenant_salt=TENANT_SALT)

    # Verify: given the params, the commitments match
    assert verify_commitment(params, committed, tenant_salt=TENANT_SALT) is True

    # Verify: tampered params don't match
    tampered = {**params, "patient_name": "Bob Wilson"}
    assert verify_commitment(tampered, committed, tenant_salt=TENANT_SALT) is False


def test_plaintext_mode_is_opt_in():
    """params_visibility='plaintext' keeps all params in plaintext (opt-in only)."""
    params = {"patient_name": "John", "ssn": "123", "amount": 100}
    committed, raw = classify_params(params, tenant_salt=TENANT_SALT, params_visibility="plaintext")

    assert committed == params
    assert raw == {}


def test_no_phi_strings_in_committed():
    """Grep the committed params for any PHI string — must find zero."""
    phi_strings = ["John Doe", "123-45-6789", "chest pain", "Diabetes"]
    params = {
        "patient_name": "John Doe",
        "ssn": "123-45-6789",
        "diagnosis": "Type 2 Diabetes",
        "note": "Patient reports chest pain after exercise.",
    }

    committed, _ = classify_params(params, tenant_salt=TENANT_SALT)

    import json
    committed_str = json.dumps(committed, default=str)
    for phi in phi_strings:
        assert phi not in committed_str, f"PHI string '{phi}' found in committed params"
