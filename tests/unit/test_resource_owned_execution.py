"""Cloud-side tests for the resource-owned execution service (Prompt 9).

These tests cover the Cloud layer of the Prompt-9 formalisation:

  * Tenant authorisation: tenants not on the whitelist are rejected.
  * Endpoint whitelisting: resources not on the tenant's whitelist are rejected.
  * Result wrapping: the Cloud service returns the ModeAwareExecutionResult
    from the Permit-side submission client unchanged.
  * Reconciliation flag: ``requires_reconciliation`` correctly identifies
    non-final resource_owned states that need follow-up.
  * Audit log: the service emits an info log on every submit.

The hard rules (forged receipt -> outcome_unknown, submission != execution)
are tested in the Permit repo; these Cloud tests focus on Cloud-specific
concerns.
"""

from __future__ import annotations

import logging

import pytest
from actenon.execution.mode_aware import (
    ModeAwareExecutionResult,
    ResourceReceiptVerifier,
    ResourceSigningKey,
    build_resource_owned_result,
)
from actenon_protocol.execution_results import (
    BrokeredExecutionState,
    ResourceOwnedExecutionState,
)

from app.services.resource_owned_execution import (
    ResourceEndpointConfig,
    ResourceEndpointNotWhitelistedError,
    ResourceOwnedExecutionService,
    TenantNotAuthorisedForResourceOwnedError,
)


@pytest.fixture
def endpoint_a() -> ResourceEndpointConfig:
    return ResourceEndpointConfig(
        resource_id="stripe-resource",
        endpoint_url="https://resource.example.invalid/submit",
        signing_key_id="stripe-key-1",
        signing_key_secret=b"stripe-secret-not-real",
        timeout_seconds=5.0,
    )


@pytest.fixture
def service_with_endpoint(endpoint_a) -> ResourceOwnedExecutionService:
    svc = ResourceOwnedExecutionService()
    svc.register_endpoint(endpoint_a)
    svc.authorise_tenant("tenant-acme", {"stripe-resource"})
    return svc


def _make_submitted_result() -> ModeAwareExecutionResult:
    return build_resource_owned_result(
        state=ResourceOwnedExecutionState.SUBMITTED,
        verified_by="example-boundary",
        executed_by="stripe-resource",
        attempt_id="exec_test",
        occurred_at="2026-07-22T10:00:00Z",
        submission_reference="sub_1",
    )


def _make_succeeded_result() -> ModeAwareExecutionResult:
    # Build a verifier with the real key so the receipt verifies.
    import hashlib
    import hmac
    import json

    secret = b"stripe-secret-not-real"
    key = ResourceSigningKey(
        resource_id="stripe-resource",
        key_id="stripe-key-1",
        secret=secret,
    )
    v = ResourceReceiptVerifier()
    v.register_key(key)
    body = {
        "resource_id": "stripe-resource",
        "charge_id": "ch_1",
        "signing_key_id": "stripe-key-1",
    }
    receipt = dict(body)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    receipt["signature"] = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return build_resource_owned_result(
        state=ResourceOwnedExecutionState.SUCCEEDED,
        verified_by="example-boundary",
        executed_by="stripe-resource",
        attempt_id="exec_test_ok",
        occurred_at="2026-07-22T10:00:00Z",
        provider_execution_observed=True,
        resource_receipt_received=True,
        resource_receipt=receipt,
        resource_receipt_verifier=v,
        submission_reference="sub_1",
    )


def _make_outcome_unknown_result() -> ModeAwareExecutionResult:
    return build_resource_owned_result(
        state=ResourceOwnedExecutionState.OUTCOME_UNKNOWN,
        verified_by="example-boundary",
        executed_by="stripe-resource",
        attempt_id="exec_test_unknown",
        occurred_at="2026-07-22T10:00:00Z",
        submission_reference="sub_2",
    )


# ---------------------------------------------------------------------------
# Tenant authorisation
# ---------------------------------------------------------------------------


def test_tenant_not_authorised_is_rejected(service_with_endpoint):
    """A tenant with no whitelist entry is rejected."""
    with pytest.raises(TenantNotAuthorisedForResourceOwnedError):
        service_with_endpoint.submit(
            tenant_id="tenant-unknown",
            resource_id="stripe-resource",
            action=object(),
            proof={"proof_id": "p_1"},
        )


def test_resource_not_on_tenant_whitelist_is_rejected(service_with_endpoint, endpoint_a):
    """A tenant trying to submit to a resource not on its whitelist is rejected."""
    # Register a second endpoint
    service_with_endpoint.register_endpoint(
        ResourceEndpointConfig(
            resource_id="other-resource",
            endpoint_url="https://other.example.invalid/submit",
            signing_key_id="other-key-1",
            signing_key_secret=b"other-secret",
        )
    )
    # tenant-acme is only whitelisted for stripe-resource
    with pytest.raises(ResourceEndpointNotWhitelistedError):
        service_with_endpoint.submit(
            tenant_id="tenant-acme",
            resource_id="other-resource",
            action=object(),
            proof={"proof_id": "p_1"},
        )


def test_unregistered_resource_is_rejected(service_with_endpoint):
    """Submitting to an unregistered resource_id is rejected."""
    with pytest.raises(ResourceEndpointNotWhitelistedError):
        service_with_endpoint.submit(
            tenant_id="tenant-acme",
            resource_id="never-registered",
            action=object(),
            proof={"proof_id": "p_1"},
        )


# ---------------------------------------------------------------------------
# Result wrapping
# ---------------------------------------------------------------------------


def test_submit_returns_result_from_client(service_with_endpoint, monkeypatch):
    """The service returns whatever the Permit-side client returns,
    unchanged. The Cloud layer does not modify the result."""

    # Inject a fake client factory.
    expected_result = _make_submitted_result()

    def _fake_factory(endpoint, resource_id, verifier, timeout):
        def _submit(action, proof, *, pccb_id=None, action_hash=None):
            return expected_result
        return _submit

    service_with_endpoint.client_factory = _fake_factory

    result = service_with_endpoint.submit(
        tenant_id="tenant-acme",
        resource_id="stripe-resource",
        action=object(),
        proof={"proof_id": "p_1"},
    )
    assert result is expected_result
    assert result.mode == "resource_owned"
    assert result.state == "submitted"


# ---------------------------------------------------------------------------
# Reconciliation flag
# ---------------------------------------------------------------------------


def test_requires_reconciliation_for_submitted(service_with_endpoint):
    r = _make_submitted_result()
    assert service_with_endpoint.requires_reconciliation(r) is True


def test_requires_reconciliation_for_outcome_unknown(service_with_endpoint):
    r = _make_outcome_unknown_result()
    assert service_with_endpoint.requires_reconciliation(r) is True


def test_does_not_require_reconciliation_for_succeeded(service_with_endpoint):
    r = _make_succeeded_result()
    assert service_with_endpoint.requires_reconciliation(r) is False


def test_does_not_require_reconciliation_for_brokered_results(service_with_endpoint):
    """The Cloud service only reconciles resource_owned results."""
    from actenon.execution import build_brokered_result

    r = build_brokered_result(
        state=BrokeredExecutionState.OUTCOME_UNKNOWN,
        verified_by="cloud-broker",
        executed_by="cloud-broker",
        attempt_id="exec_b",
        occurred_at="2026-07-22T10:00:00Z",
        provider_execution_observed=False,
    )
    assert service_with_endpoint.requires_reconciliation(r) is False


# ---------------------------------------------------------------------------
# is_final
# ---------------------------------------------------------------------------


def test_is_final_for_succeeded(service_with_endpoint):
    r = _make_succeeded_result()
    assert service_with_endpoint.is_final(r) is True


def test_is_not_final_for_submitted(service_with_endpoint):
    r = _make_submitted_result()
    assert service_with_endpoint.is_final(r) is False


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def test_submit_emits_audit_log(service_with_endpoint, caplog):
    """The service logs an info record on every submit."""

    def _fake_factory(endpoint, resource_id, verifier, timeout):
        def _submit(action, proof, *, pccb_id=None, action_hash=None):
            return _make_submitted_result()
        return _submit

    service_with_endpoint.client_factory = _fake_factory

    with caplog.at_level(logging.INFO, logger="action_control_plane.workflow"):
        service_with_endpoint.submit(
            tenant_id="tenant-acme",
            resource_id="stripe-resource",
            action=object(),
            proof={"proof_id": "p_audit"},
            pccb_id="pccb_audit",
        )

    # The service uses the action_control_plane.workflow logger (Cloud convention).
    # Look for the structured log event.
    found = False
    for record in caplog.records:
        if "resource_owned_execution_submitted" in record.getMessage():
            found = True
            break
    assert found, "expected resource_owned_execution_submitted log event"


# ---------------------------------------------------------------------------
# Verifier config
# ---------------------------------------------------------------------------


def test_build_verifier_for_registered_resource_has_key(service_with_endpoint):
    """The verifier built for a registered resource has the resource's signing key."""
    v = service_with_endpoint.build_verifier_for("stripe-resource")
    assert "stripe-key-1" in v.keys


def test_build_verifier_for_unregistered_resource_raises(service_with_endpoint):
    """Building a verifier for an unregistered resource raises."""
    from app.services.resource_owned_execution import ResourceOwnedExecutionError

    with pytest.raises(ResourceOwnedExecutionError):
        service_with_endpoint.build_verifier_for("never-registered")
