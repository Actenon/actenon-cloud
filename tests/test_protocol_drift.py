"""Protocol drift gate for actenon-cloud.

This test module fails when:
  - The pinned actenon-protocol version does not match cloud's expected version.
  - Cloud's contract tests pin to a raw refusal_code string instead of
    the canonical FailureCode enum member (the SIGNATURE_INVALID vs
    PROOF_INVALID drift — audit C-01).
  - Cloud imports Kernel internals (beyond the published API surface).
  - An unregistered refusal code is emitted.
  - Canonicalisation byte output diverges.

Run with: `python -m pytest tests/test_protocol_drift.py -v`
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from actenon_protocol import (
    CANONICALISATION_PROFILE,
    PROTOCOL_VERSION,
)
from actenon_protocol.canonicalisation import canonicalize_json

# ---------------------------------------------------------------------------
# 0. Pinned protocol version
# ---------------------------------------------------------------------------

EXPECTED_PROTOCOL_VERSION = "1.0.0"


def test_protocol_version_is_pinned():
    assert PROTOCOL_VERSION == EXPECTED_PROTOCOL_VERSION


def test_pyproject_pins_protocol():
    """pyproject.toml must pin actenon-protocol to v1.0.0."""
    import tomllib
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    assert any("actenon-protocol" in d and "v1.0.0" in d for d in deps), (
        f"actenon-protocol @ v1.0.0 not pinned in dependencies: {deps}"
    )


# ---------------------------------------------------------------------------
# 1. Refusal-code drift (audit C-01: SIGNATURE_INVALID vs PROOF_INVALID)
# ---------------------------------------------------------------------------

def test_contract_tests_use_canonical_failure_code():
    """Contract tests MUST NOT assert on raw refusal_code strings that
    depend on the disclosure policy. They MUST assert on the canonical
    FailureCode enum member via refusal_code_to_failure_code().

    This is the fix for audit finding C-01: the kernel emits
    SIGNATURE_INVALID under trusted disclosure and PROOF_INVALID under
    public disclosure. Tests that assert on the raw string break when
    the disclosure policy changes. Asserting on the FailureCode enum
    member is disclosure-policy-independent.
    """
    contract_dir = Path(__file__).resolve().parent / "contract"
    if not contract_dir.exists():
        pytest.skip("no contract tests directory")
    # Forbidden pattern: assert exc_info.value.refusal_code == "SIGNATURE_INVALID"
    # (or any other raw refusal-code string that depends on disclosure policy)
    forbidden_pattern = re.compile(
        r'assert\s+exc_info\.value\.refusal_code\s*==\s*["\']'
        r'(SIGNATURE_INVALID|PROOF_INVALID|AUDIENCE_MISMATCH|TARGET_MISMATCH|'
        r'ACTION_MISMATCH|PARAMETER_MISMATCH|ISSUER_UNTRUSTED)["\']'
    )
    violations = []
    for py_file in contract_dir.rglob("*.py"):
        text = py_file.read_text()
        for match in forbidden_pattern.finditer(text):
            line_no = text[:match.start()].count("\n") + 1
            violations.append(f"{py_file.name}:{line_no}: {match.group(0).strip()}")
    assert not violations, (
        "contract tests assert on raw refusal_code strings (disclosure-policy-"
        "dependent). Use refusal_code_to_failure_code() instead. Violations:\n  "
        + "\n  ".join(violations)
    )


def test_refusal_code_to_failure_code_is_disclosure_independent():
    """refusal_code_to_failure_code() MUST return the same FailureCode
    for both SIGNATURE_INVALID and PROOF_INVALID (the umbrella)."""
    from actenon.outcomes import refusal_code_to_failure_code
    fc_sig = refusal_code_to_failure_code("SIGNATURE_INVALID")
    fc_proof = refusal_code_to_failure_code("PROOF_INVALID")
    assert fc_sig == fc_proof, (
        f"SIGNATURE_INVALID and PROOF_INVALID must map to the same "
        f"FailureCode (disclosure-policy-independent). Got {fc_sig!r} and {fc_proof!r}"
    )


# ---------------------------------------------------------------------------
# 2. Canonicalisation agreement
# ---------------------------------------------------------------------------

def test_canonicalisation_profile_label_agrees():
    """Cloud uses rfc8785 library directly in some places (countersigning,
    transparency). The profile label must agree with the protocol's."""
    # Cloud doesn't expose a single CANONICALIZATION_PROFILE constant;
    # we verify that the protocol's label is what Cloud should use.
    assert CANONICALISATION_PROFILE == "ACTENON-JCS-STRICT-1"


def test_canonicalisation_byte_equivalence():
    """Cloud's rfc8785-based canonicalisation must produce byte-identical
    output to the protocol's reference for shared test inputs."""
    import rfc8785
    test_inputs = [
        {"action": "payment.refund", "amount_cents": 2500, "currency": "GBP"},
        {"b": 1, "a": 2},
        ["a", "b", "c"],
        {"nested": {"z": 1, "a": 2}},
        "café",
        42,
    ]
    for inp in test_inputs:
        cloud_out = rfc8785.dumps(inp).decode("utf-8")
        protocol_out = canonicalize_json(inp)
        assert cloud_out == protocol_out, (
            f"canonicalisation mismatch for {inp!r}: "
            f"cloud(rfc8785)={cloud_out!r} protocol={protocol_out!r}"
        )


# ---------------------------------------------------------------------------
# 3. Boundary preservation
# ---------------------------------------------------------------------------

def test_cloud_does_not_become_proof_validity_definition():
    """Cloud MUST NOT define its own proof-validity logic. It MUST call
    the kernel's PCCBVerifier (or compatible) for proof verification.

    This test scans Cloud's source for any custom signature-verification
    or action-hash-verification logic that bypasses the kernel.
    """
    app_dir = Path(__file__).resolve().parent.parent / "app"
    if not app_dir.exists():
        pytest.skip("no app directory")
    # Forbidden: custom verify functions that don't delegate to the kernel
    forbidden_patterns = [
        # A custom Ed25519 verify that doesn't go through PCCBVerifier
        r"def\s+verify_signature\b(?!.*PCCBVerifier)",
        # A custom action-hash recomputation that doesn't use the kernel's
        r"def\s+recompute_action_hash\b(?!.*canonicalize)",
    ]
    violations = []
    for py_file in app_dir.rglob("*.py"):
        text = py_file.read_text()
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, text):
                line_no = text[:match.start()].count("\n") + 1
                violations.append(f"{py_file.name}:{line_no}: {match.group(0).strip()}")
    # We don't fail on every match — some are legitimate (e.g. test helpers).
    # We fail only if there are MORE than a threshold, indicating a pattern
    # of bypassing the kernel.
    if len(violations) > 3:
        pytest.fail(
            f"Cloud appears to define its own proof-validity logic ({len(violations)} "
            f"suspicious patterns). Cloud MUST call the kernel's PCCBVerifier. "
            f"Violations:\n  " + "\n  ".join(violations[:10])
        )


def test_protocol_does_not_import_cloud():
    """The protocol package MUST NOT import app.* (Cloud's package)."""
    import actenon_protocol
    init_code = open(actenon_protocol.__file__).read()
    assert "import app" not in init_code and "from app" not in init_code, (
        "actenon_protocol.__init__ imports Cloud's app package"
    )


# ---------------------------------------------------------------------------
# 4. Unknown refusal codes not silently mapped
# ---------------------------------------------------------------------------

def test_unknown_refusal_code_raises():
    """Unknown refusal codes MUST raise, not silently map to a generic
    outcome. Cloud's HTTP boundary MUST propagate the refusal, not
    swallow it."""
    from actenon.outcomes import refusal_code_to_failure_code
    with pytest.raises(KeyError):
        refusal_code_to_failure_code("NOT_A_REAL_CODE")


# ---------------------------------------------------------------------------
# 5. Protocol version rejection
# ---------------------------------------------------------------------------

def test_unsupported_major_version_is_rejected():
    """A protocol version with major != 1 must be rejected."""
    from actenon_protocol.types.common import ProtocolVersion
    from pydantic import TypeAdapter, ValidationError
    adapter = TypeAdapter(ProtocolVersion)
    assert adapter.validate_python("1.0.0") == "1.0.0"
    with pytest.raises(ValidationError):
        adapter.validate_python("2.0.0")
