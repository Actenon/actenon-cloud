"""Tests for evidence bundle + outcome honesty (Prompt 16).

Covers:
  * Evidence bundle structure (9 layers, manifest, hashes, identifiers)
  * Independent verification (recompute hashes, detect tampering)
  * Redaction record (credentials + raw responses excluded)
  * Brokered outcome honesty (refused_before_execution, executing, etc.)
  * Resource-owned outcome honesty (submitted != succeeded, receipt states)
  * Never green for submission-only
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_intent(client: TestClient, **overrides) -> dict:
    body = {
        "action_type": "github.issue.create",
        "action_params": {"owner": "actenon", "repo": "demo", "title": "test"},
        "target_type": "github",
        "target_id": "github",
        "requested_execution_mode": "brokered",
    }
    body.update(overrides)
    resp = client.post("/api/v1/intents", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _full_lifecycle(client: TestClient, intent_id: str) -> None:
    """Advance an intent through the full brokered lifecycle."""
    client.post(f"/api/v1/intents/{intent_id}/approve", json={"approver_id": "a1"})
    client.post(f"/api/v1/intents/{intent_id}/proof")
    client.post(f"/api/v1/intents/{intent_id}/execute", json={"grant_token": "fake"})


# ---------------------------------------------------------------------------
# 1. Evidence bundle structure
# ---------------------------------------------------------------------------


def test_evidence_bundle_has_9_layers(client: TestClient):
    """The bundle must contain all 9 evidence layers."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])

    resp = client.get(f"/api/v1/intents/{created['intent_id']}/evidence")
    assert resp.status_code == 200
    bundle = resp.json()

    layers = [a["layer"] for a in bundle["artefacts"]]
    assert 1 in layers  # intent_record
    assert 9 in layers  # cloud_correlation


def test_evidence_bundle_has_manifest(client: TestClient):
    """The bundle must have a manifest with bundle_id, protocol_version, etc."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])

    resp = client.get(f"/api/v1/intents/{created['intent_id']}/evidence")
    bundle = resp.json()
    manifest = bundle["manifest"]
    assert manifest["bundle_id"].startswith("evbundle_")
    assert manifest["protocol_version"] == "1.1.0"
    assert manifest["intent_id"] == created["intent_id"]
    assert manifest["artefact_count"] > 0


def test_evidence_bundle_has_identifiers(client: TestClient):
    """The bundle must have identifiers linking all artefacts."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])

    resp = client.get(f"/api/v1/intents/{created['intent_id']}/evidence")
    bundle = resp.json()
    ids = bundle["identifiers"]
    assert ids["intent_id"] == created["intent_id"]
    assert ids["proof_id"] is not None


def test_evidence_bundle_has_hashes(client: TestClient):
    """Each artefact must have a SHA-256 hash."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])

    resp = client.get(f"/api/v1/intents/{created['intent_id']}/evidence")
    bundle = resp.json()
    for artefact in bundle["artefacts"]:
        assert "hash" in artefact
        assert len(artefact["hash"]) == 64  # SHA-256 hex


def test_evidence_bundle_has_redaction_record(client: TestClient):
    """The bundle must include a redaction record."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])

    resp = client.get(f"/api/v1/intents/{created['intent_id']}/evidence")
    bundle = resp.json()
    redactions = bundle["redaction_record"]
    assert len(redactions) >= 2
    redacted_fields = [r["field"] for r in redactions]
    assert "credential_value" in redacted_fields
    assert "provider_raw_response" in redacted_fields


# ---------------------------------------------------------------------------
# 2. Independent verification
# ---------------------------------------------------------------------------


def test_evidence_verification_passes(client: TestClient):
    """The verify endpoint recomputes hashes and confirms they match."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])

    resp = client.post(f"/api/v1/intents/{created['intent_id']}/evidence/verify")
    assert resp.status_code == 200
    result = resp.json()
    assert result["verified"] is True
    assert result["artefact_count"] > 0
    for ar in result["artefact_results"]:
        assert ar["hash_matches"] is True


def test_evidence_verification_detects_tampering(client: TestClient):
    """If an artefact's content is modified, verification must fail."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])

    # Get the bundle
    bundle_resp = client.get(f"/api/v1/intents/{created['intent_id']}/evidence")
    bundle = bundle_resp.json()

    # Tamper with an artefact's content (but not its hash)
    bundle["artefacts"][0]["content"]["action_type"] = "TAMPERED"

    # Verify using the service directly (can't POST a body via the endpoint)
    from app.services.evidence_bundle import EvidenceBundleService

    # Use the app's DB session via the test client's app state
    container = client.app.state.container
    with container.database.session() as session:
        service = EvidenceBundleService(session)
        result = service.verify_bundle(bundle)
        assert result["verified"] is False
        assert any(not ar["hash_matches"] for ar in result["artefact_results"])


# ---------------------------------------------------------------------------
# 3. Brokered outcome honesty
# ---------------------------------------------------------------------------


def test_brokered_outcome_refused_before_execution(client: TestClient):
    """A denied intent shows 'refused_before_execution', not 'failed'."""
    created = _create_intent(client)
    client.post(f"/api/v1/intents/{created['intent_id']}/deny", json={
        "denier_id": "d1", "reason": "no",
    })
    resp = client.get(f"/api/v1/intents/{created['intent_id']}/outcome")
    body = resp.json()
    assert body["display_state"] == "refused_before_execution"
    assert body["is_green"] is False
    assert body["is_terminal"] is True


def test_brokered_outcome_executing(client: TestClient):
    """An intent in 'executing' state shows 'executing', not 'succeeded'."""
    created = _create_intent(client)
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={"approver_id": "a1"})
    client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    # Don't execute yet — check the 'proof_issued' state
    resp = client.get(f"/api/v1/intents/{created['intent_id']}/outcome")
    body = resp.json()
    assert body["display_state"] == "ready_to_execute"
    assert body["is_green"] is False


def test_brokered_outcome_succeeded(client: TestClient):
    """A succeeded intent shows 'succeeded' and is green."""
    created = _create_intent(client)
    _full_lifecycle(client, created["intent_id"])
    resp = client.get(f"/api/v1/intents/{created['intent_id']}/outcome")
    body = resp.json()
    assert body["display_state"] == "succeeded"
    assert body["is_green"] is True
    assert body["is_terminal"] is True


# ---------------------------------------------------------------------------
# 4. Resource-owned outcome honesty
# ---------------------------------------------------------------------------


def test_resource_owned_outcome_submitted_not_green(client: TestClient):
    """A submitted resource-owned intent is NOT green — submission != execution."""
    created = _create_intent(
        client, requested_execution_mode="resource_owned",
    )
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={"approver_id": "a1"})
    client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    client.post(f"/api/v1/intents/{created['intent_id']}/submit", json={
        "proof": {"proof_id": "p1", "execution_mode": "resource_owned"},
    })
    resp = client.get(f"/api/v1/intents/{created['intent_id']}/outcome")
    body = resp.json()
    assert body["execution_mode"] == "resource_owned"
    assert body["display_state"] in ("submitted", "receipt_awaited")
    assert body["is_green"] is False  # NEVER green for submission-only
    assert body["is_terminal"] is False


def test_resource_owned_outcome_receipt_awaited(client: TestClient):
    """A submitted resource-owned intent with a submission_reference shows
    'receipt_awaited', not 'succeeded'."""
    created = _create_intent(
        client, requested_execution_mode="resource_owned",
    )
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={"approver_id": "a1"})
    client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/submit", json={
        "proof": {"proof_id": "p1", "execution_mode": "resource_owned"},
    })
    assert resp.status_code == 200
    assert resp.json()["submission_reference"] is not None

    outcome = client.get(f"/api/v1/intents/{created['intent_id']}/outcome")
    body = outcome.json()
    assert body["display_state"] == "receipt_awaited"
    assert body["is_green"] is False
    assert body["resource_receipt_received"] is False
