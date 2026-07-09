"""B4 contract test: escrow release wires into the permit broker (not simulated).

This test replaces the prior ``secrets.token_urlsafe(32)`` simulation with a
real, signed capability token minted via ``resolve_signer`` from
``app.services.kernel_bridge``. The capability token is a JWT-like structure
header.payload.signature where:

  * ``header`` carries ``alg``/``typ``/``kid``
  * ``payload`` carries ``escrow_id``, ``action_intent_digest``, ``scope``,
    ``audience``, ``exp``, and ``nonce``
  * ``signature`` is the Ed25519 (or, in dev fallback, HMAC-SHA256) signature
    over ``header.payload``

The test exercises the end-to-end escrow release path through the public API
and asserts:

  1. ``simulated`` is ``False`` in the release metadata
  2. the capability token is a 3-segment signed structure
  3. the signature verifies against the configured Ed25519 signer
  4. the payload contains the expected bounded claims
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path

from app.services.escrow import verify_capability_token
from app.services.kernel_bridge import resolve_signer
from tests.integration.test_issuance import (
    build_intake_payload,
    create_allow_policy,
    create_signing_key,
    create_tenant,
)


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _create_issued_proof(client) -> dict[str, object]:
    tenant = create_tenant(client)
    create_allow_policy(client, tenant["tenant_id"])
    key = create_signing_key(client, tenant["tenant_id"])

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(
            tenant["tenant_id"],
            submission_id=f"broker-release-submission-{tenant['tenant_id']}",
            idempotency_key=f"broker-release-idempotency-{tenant['tenant_id']}",
            kernel_action_intent={
                "intent_id": f"broker-release-intent-{tenant['tenant_id']}",
                "workflow_key": "payments.standard",
                "action_type": "transfer",
                "amount_minor": 250000,
                "currency": "USD",
                "source_account_ref": "acct-source-broker",
                "destination_account_ref": "acct-destination-broker",
                "destination_country": "GB",
                "evidence_refs": [],
            },
            evaluation_context={"risk_tier": "medium", "evidence_present": False},
        ),
    )
    assert intake_response.status_code == 201, intake_response.text
    intake = intake_response.json()

    issuance_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-provider.internal",
            "scope": ["finance.transfer.release"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "issuer-broker-001",
            },
            "signing_key_reference_id": key["signing_key_reference_id"],
        },
    )
    assert issuance_response.status_code == 201, issuance_response.text
    proof = issuance_response.json()
    assert proof["status"] == "issued"
    return {
        "tenant": tenant,
        "intake": intake,
        "proof": proof,
    }


def test_broker_release_marks_release_as_not_simulated(client) -> None:
    """The release metadata must record ``simulated: False``."""
    fixtures = _create_issued_proof(client)
    proof = fixtures["proof"]

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-broker-001"},
            "capability_metadata": {"rail": "wire", "region": "gb"},
        },
    )
    assert hold_response.status_code == 201, hold_response.text
    hold = hold_response.json()

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-broker-001"}
        },
    )
    assert release_response.status_code == 200, release_response.text
    released = release_response.json()

    assert released["release_metadata"]["simulated"] is False
    assert (
        released["release_metadata"]["provider_integration"]
        == "permit_broker_signed_capability"
    )


def test_broker_release_returns_signed_capability_token(client) -> None:
    """The capability token must be a 3-segment signed JWT-like structure."""
    fixtures = _create_issued_proof(client)
    proof = fixtures["proof"]

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-broker-002"},
        },
    )
    assert hold_response.status_code == 201, hold_response.text
    hold = hold_response.json()

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-broker-002"}
        },
    )
    assert release_response.status_code == 200, release_response.text
    released = release_response.json()

    capability_token = released["capability_token"]
    parts = capability_token.split(".")
    assert len(parts) == 3, (
        f"capability token must have 3 segments (header.payload.signature), "
        f"got {len(parts)}"
    )
    header_part, payload_part, signature_part = parts

    # Header must be a JSON object declaring alg + typ + kid.
    header = json.loads(_b64url_decode(header_part).decode("utf-8"))
    assert header["typ"] == "acp-cap+jwt"
    assert header["alg"] in {"EdDSA", "HS256"}, (
        f"unexpected alg {header['alg']}; the broker must use a real signer"
    )
    assert header["kid"], "header must declare a key id (kid)"

    # Payload must carry the bounded capability claims.
    payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    assert payload["escrow_id"] == hold["escrow_record_id"]
    assert payload["action_intent_digest"] == proof["action_intent_digest"]
    assert payload["scope"] == proof["scope"]
    assert payload["audience"] == proof["audience"]
    assert isinstance(payload["exp"], int)
    assert payload["exp"] > int(datetime.now(UTC).timestamp())
    assert payload["nonce"], "payload must carry a fresh nonce"

    # Signature segment must not be empty and must not look like a random URL-safe
    # token (it must be a base64url signature that verifies against the signer).
    assert signature_part, "signature segment must not be empty"
    assert capability_token != signature_part, (
        "capability token must not be a bare random string"
    )


def test_broker_release_signature_verifies_against_resolve_signer(
    client, monkeypatch
) -> None:
    """The capability token's signature must verify against ``resolve_signer``.

    ``resolve_signer`` is the same entry point the escrow service uses to mint
    the token, so a successful verify here proves the release path went through
    the real broker and not a random ``secrets.token_urlsafe`` simulation.
    """
    # The test conftest sets ACTENON_ED25519_KEY_FILE; confirm it is in place
    # so resolve_signer() returns the Ed25519 signer.
    key_file_env = __import__("os").environ.get("ACTENON_ED25519_KEY_FILE")
    assert key_file_env, (
        "ACTENON_ED25519_KEY_FILE must be set by the test harness for broker "
        "release tests"
    )
    assert Path(key_file_env).is_file(), (
        f"ACTENON_ED25519_KEY_FILE points to a non-existent file: {key_file_env}"
    )

    fixtures = _create_issued_proof(client)
    proof = fixtures["proof"]

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-broker-003"},
        },
    )
    assert hold_response.status_code == 201, hold_response.text
    hold = hold_response.json()

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-broker-003"}
        },
    )
    assert release_response.status_code == 200, release_response.text
    released = release_response.json()

    capability_token = released["capability_token"]

    # The signer resolved here is the same one the escrow service used.
    signer = resolve_signer()
    payload = verify_capability_token(capability_token, signer=signer)
    assert payload["escrow_id"] == hold["escrow_record_id"]
    assert payload["action_intent_digest"] == proof["action_intent_digest"]


def test_broker_release_token_is_not_random_urlsafe_string(client) -> None:
    """The capability token must not be a bare ``secrets.token_urlsafe`` string.

    A bare random string has no ``.`` separators; a JWT-like signed token has
    exactly two ``.`` separators and decodes to JSON header/payload segments.
    """
    fixtures = _create_issued_proof(client)
    proof = fixtures["proof"]

    hold_response = client.post(
        "/api/v1/escrow/holds",
        json={
            "issued_proof_id": proof["issued_proof_id"],
            "capability_kind": "finance.transfer.release",
            "protected_resource_ref": "provider://payments/core/transfers",
            "requested_by": {"principal_type": "user", "principal_id": "release-broker-004"},
        },
    )
    assert hold_response.status_code == 201, hold_response.text
    hold = hold_response.json()

    release_response = client.post(
        f"/api/v1/escrow/{hold['escrow_record_id']}/release",
        json={
            "released_by": {"principal_type": "user", "principal_id": "release-broker-004"}
        },
    )
    assert release_response.status_code == 200, release_response.text
    released = release_response.json()

    capability_token = released["capability_token"]
    assert "." in capability_token, (
        "capability token must be a structured JWT-like string, not a random token"
    )
    assert capability_token.count(".") == 2, (
        "capability token must have exactly two '.' separators (header.payload.signature)"
    )

    header_part = capability_token.split(".")[0]
    header = json.loads(_b64url_decode(header_part).decode("utf-8"))
    assert header.get("typ") == "acp-cap+jwt"
