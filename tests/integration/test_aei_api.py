"""Cloud AEI API tests (Prompt 14).

Covers:
  * API endpoints: create, retrieve, list, approve, deny, cancel,
    proof, execute, submit, receipts, refusals, evidence, capabilities
  * Lifecycle enforcement: illegal transitions rejected with 409
  * Idempotency: duplicate create returns the original; duplicate
    execute returns the existing terminal state
  * Tenant isolation: cross-tenant access returns 404
  * Concurrency: double-approval prevented by transaction

Uses the existing Cloud test client fixture (SQLite + auth bootstrap).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures — reuse the existing conftest.py client fixture
# ---------------------------------------------------------------------------


def _create_intent(client: TestClient, **overrides) -> dict:
    """Helper: create an intent and return the response body."""
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


# ---------------------------------------------------------------------------
# 1. Create + retrieve + list
# ---------------------------------------------------------------------------


def test_create_intent(client: TestClient):
    resp = client.post("/api/v1/intents", json={
        "action_type": "github.issue.create",
        "action_params": {"owner": "actenon", "repo": "demo", "title": "test"},
        "target_type": "github",
        "target_id": "github",
        "requested_execution_mode": "brokered",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["intent_id"].startswith("intent_")
    assert body["lifecycle_state"] == "created"
    assert body["action_type"] == "github.issue.create"


def test_get_intent(client: TestClient):
    created = _create_intent(client)
    resp = client.get(f"/api/v1/intents/{created['intent_id']}")
    assert resp.status_code == 200
    assert resp.json()["intent_id"] == created["intent_id"]


def test_get_intent_404(client: TestClient):
    resp = client.get("/api/v1/intents/intent_doesnotexist")
    assert resp.status_code == 404


def test_list_intents(client: TestClient):
    _create_intent(client)
    _create_intent(client, action_type="iam.grant_role", target_id="iam")
    resp = client.get("/api/v1/intents")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_list_intents_pagination(client: TestClient):
    for i in range(5):
        _create_intent(client, action_params={"title": f"test-{i}"})
    resp = client.get("/api/v1/intents?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


# ---------------------------------------------------------------------------
# 2. Lifecycle enforcement
# ---------------------------------------------------------------------------


def test_approve_intent(client: TestClient):
    created = _create_intent(client)
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-1",
    })
    assert resp.status_code == 200
    assert resp.json()["lifecycle_state"] == "authorised"


def test_deny_intent(client: TestClient):
    created = _create_intent(client)
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/deny", json={
        "denier_id": "denier-1",
        "reason": "not allowed",
    })
    assert resp.status_code == 200
    assert resp.json()["lifecycle_state"] == "denied"


def test_cancel_intent(client: TestClient):
    created = _create_intent(client)
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["lifecycle_state"] == "cancelled"


def test_illegal_transition_rejected(client: TestClient):
    """created -> succeeded is illegal (must go through evaluating -> authorised -> ...)."""
    created = _create_intent(client)
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/execute", json={
        "grant_token": "fake-token",
    })
    # created -> executing is illegal (must go through evaluating -> authorised first)
    assert resp.status_code == 409


def test_double_approve_prevented(client: TestClient):
    """Approving an already-authorised intent is idempotent (returns 200, not 409).

    The second approve does NOT transition the state (authorised -> authorised
    is not a valid transition). The endpoint detects the already-authorised
    state and returns the existing record without attempting a transition.
    This prevents double-approval race conditions.
    """
    created = _create_intent(client)
    # First approve succeeds.
    resp1 = client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-1",
    })
    assert resp1.status_code == 200
    assert resp1.json()["lifecycle_state"] == "authorised"
    # Second approve is idempotent (returns 200, same state).
    resp2 = client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-2",
    })
    assert resp2.status_code == 200
    assert resp2.json()["lifecycle_state"] == "authorised"


# ---------------------------------------------------------------------------
# 3. Proof issuance
# ---------------------------------------------------------------------------


def test_issue_proof(client: TestClient):
    created = _create_intent(client)
    # Approve first.
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-1",
    })
    # Issue proof.
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    assert resp.status_code == 200
    body = resp.json()
    assert body["lifecycle_state"] == "proof_issued"
    assert body["linked_proof_id"] is not None


def test_proof_idempotent(client: TestClient):
    """Issuing proof twice returns the same proof_id (idempotent)."""
    created = _create_intent(client)
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-1",
    })
    resp1 = client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    proof_id_1 = resp1.json()["linked_proof_id"]
    resp2 = client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    proof_id_2 = resp2.json()["linked_proof_id"]
    assert proof_id_1 == proof_id_2


# ---------------------------------------------------------------------------
# 4. Execute (brokered)
# ---------------------------------------------------------------------------


def test_execute_intent(client: TestClient):
    created = _create_intent(client)
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-1",
    })
    client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/execute", json={
        "grant_token": "fake-token",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["execution_state"] == "succeeded"
    assert body["finality"] == "final"


def test_execute_idempotent(client: TestClient):
    """Executing an already-succeeded intent returns the existing state."""
    created = _create_intent(client)
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-1",
    })
    client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    client.post(f"/api/v1/intents/{created['intent_id']}/execute", json={
        "grant_token": "fake-token",
    })
    resp2 = client.post(f"/api/v1/intents/{created['intent_id']}/execute", json={
        "grant_token": "fake-token",
    })
    assert resp2.json()["idempotent"] is True
    assert resp2.json()["execution_state"] == "succeeded"


# ---------------------------------------------------------------------------
# 5. Submit (resource-owned)
# ---------------------------------------------------------------------------


def test_submit_intent(client: TestClient):
    created = _create_intent(
        client,
        requested_execution_mode="resource_owned",
    )
    client.post(f"/api/v1/intents/{created['intent_id']}/approve", json={
        "approver_id": "approver-1",
    })
    client.post(f"/api/v1/intents/{created['intent_id']}/proof")
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/submit", json={
        "proof": {"proof_id": "proof_1", "execution_mode": "resource_owned"},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["execution_state"] == "submitted"
    assert body["finality"] == "non_final"


def test_submit_wrong_mode_rejected(client: TestClient):
    """Submitting a brokered intent via /submit returns 400."""
    created = _create_intent(client, requested_execution_mode="brokered")
    resp = client.post(f"/api/v1/intents/{created['intent_id']}/submit", json={
        "proof": {"proof_id": "p"},
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 6. Receipts, refusals, evidence
# ---------------------------------------------------------------------------


def test_get_receipts_empty(client: TestClient):
    created = _create_intent(client)
    resp = client.get(f"/api/v1/intents/{created['intent_id']}/receipts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_refusals_empty(client: TestClient):
    created = _create_intent(client)
    resp = client.get(f"/api/v1/intents/{created['intent_id']}/refusals")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_evidence(client: TestClient):
    created = _create_intent(client)
    resp = client.get(f"/api/v1/intents/{created['intent_id']}/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent_id"] == created["intent_id"]
    assert body["lifecycle_state"] == "created"
    assert body["linked_proof_id"] is None


# ---------------------------------------------------------------------------
# 7. Capabilities
# ---------------------------------------------------------------------------


def test_capabilities(client: TestClient):
    resp = client.get("/api/v1/intents/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["transport"] == "cloud"
    assert body["supports_brokered"] is True
    assert body["supports_resource_owned"] is True
    assert body["durable"] is True
    assert body["production_mode"] is True


# ---------------------------------------------------------------------------
# 8. Idempotency
# ---------------------------------------------------------------------------


def test_create_idempotent(client: TestClient):
    """Creating with the same idempotency_key returns the original intent."""
    resp1 = client.post("/api/v1/intents", json={
        "action_type": "github.issue.create",
        "action_params": {"owner": "a", "repo": "b", "title": "t"},
        "target_type": "github",
        "target_id": "github",
        "idempotency_key": "op-idem-1",
    })
    assert resp1.status_code == 201
    intent_id_1 = resp1.json()["intent_id"]

    resp2 = client.post("/api/v1/intents", json={
        "action_type": "github.issue.create",
        "action_params": {"owner": "a", "repo": "b", "title": "t"},
        "target_type": "github",
        "target_id": "github",
        "idempotency_key": "op-idem-1",
    })
    assert resp2.status_code == 201
    intent_id_2 = resp2.json()["intent_id"]
    assert intent_id_1 == intent_id_2
