"""Tests for PermitGatewayBridge + reconciliation worker (Prompt 10 follow-up).

Covers:
  * Bridge builds a Gateway with DurableCloudIntentStore.
  * Resource clients are registered for every whitelisted endpoint.
  * Reconciliation worker advances non-final intents to succeeded/failed.
  * Worker handles missing proof / missing client gracefully.
  * Bridge startup + shutdown lifecycle.
"""

from __future__ import annotations

import asyncio

import pytest
from actenon_permit import (
    IntentLifecycle,
    ResourceOwnedSubmissionClient,
)
from actenon_permit._iam_stub import IAMStubServer

from app.database import Base, Database
from app.models.intent import AuthorisedExecutionIntentRecord
from app.services.permit_gateway_bridge import PermitGatewayBridge
from app.services.resource_owned_execution import (
    ResourceEndpointConfig,
    ResourceOwnedExecutionService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def database(tmp_path):
    db = Database(database_url=f"sqlite+pysqlite:///{tmp_path / 'bridge.db'}")
    db.connect()
    Base.metadata.create_all(bind=db.engine, tables=[AuthorisedExecutionIntentRecord.__table__])
    yield db
    Base.metadata.drop_all(bind=db.engine, tables=[AuthorisedExecutionIntentRecord.__table__])
    db.disconnect()


@pytest.fixture
def iam_stub() -> IAMStubServer:
    stub = IAMStubServer()
    stub.start()
    yield stub
    stub.stop()


@pytest.fixture
def resource_service(iam_stub: IAMStubServer) -> ResourceOwnedExecutionService:
    svc = ResourceOwnedExecutionService()
    svc.register_endpoint(ResourceEndpointConfig(
        resource_id=iam_stub.config.resource_id,
        endpoint_url=iam_stub.endpoint_url,
        signing_key_id=iam_stub.config.signing_key_id,
        signing_key_secret=iam_stub.config.signing_key_secret,
    ))
    svc.authorise_tenant("tenant-acme", {iam_stub.config.resource_id})
    return svc


@pytest.fixture
def bridge(database, resource_service, tmp_path):
    """Bridge with worker disabled (for sync tests)."""
    b = PermitGatewayBridge(
        database=database,
        resource_owned_service=resource_service,
        permit_state_path=str(tmp_path / "permit_state.db"),
        run_worker=False,
    )
    b.startup()
    yield b
    b.shutdown()


# ---------------------------------------------------------------------------
# 1. Bridge builds a Gateway with DurableCloudIntentStore
# ---------------------------------------------------------------------------


def test_bridge_gateway_uses_durable_cloud_intent_store(bridge):
    """The bridge's gateway must use a DurableCloudIntentStore."""
    mgr = bridge.intent_manager
    from actenon_permit import store_capabilities

    caps = store_capabilities(mgr.store)
    assert caps["durability_profile"] == "durable_cloud"
    assert caps["survives_host_failure"] is True


# ---------------------------------------------------------------------------
# 2. Resource clients are registered for every whitelisted endpoint
# ---------------------------------------------------------------------------


def test_bridge_registers_resource_client_for_each_endpoint(bridge, iam_stub):
    """The bridge registers a ResourceOwnedSubmissionClient for every
    endpoint in the ResourceOwnedExecutionService."""
    gw = bridge.gateway
    assert iam_stub.config.resource_id in gw.resource_clients
    client = gw.resource_clients[iam_stub.config.resource_id]
    assert isinstance(client, ResourceOwnedSubmissionClient)


def test_bridge_gateway_can_submit_to_resource(bridge, iam_stub):
    """The bridge's gateway can submit a resource-owned intent to the
    IAM stub end-to-end."""
    mgr = bridge.intent_manager
    intent = mgr.create(
        action_type="iam.grant_role",
        action_params={"subject": "alice", "role": "viewer"},
        target_type="iam",
        target_id=iam_stub.config.resource_id,
        requested_execution_mode="resource_owned",
        requester_subject="bob",
        requester_agent_id="admin-bot",
    )
    proof = {"proof_id": "proof_bridge_1", "execution_mode": "resource_owned"}
    result = bridge.gateway.submit_intent_to_resource(intent.intent_id, proof=proof)
    assert result["outcome"] == "ALLOW"
    assert result["execution_state"] == "succeeded"
    assert result["resource_receipt_verified"] is True


# ---------------------------------------------------------------------------
# 3. Reconciliation worker advances non-final intents
# ---------------------------------------------------------------------------


def test_reconcile_once_advances_non_final_intent(database, resource_service, iam_stub, tmp_path):
    """When an intent is stuck in outcome_unknown (e.g. due to a
    transient timeout), the reconciliation worker re-submits and
    advances it to succeeded."""
    bridge = PermitGatewayBridge(
        database=database,
        resource_owned_service=resource_service,
        permit_state_path=str(tmp_path / "permit_state.db"),
        run_worker=False,
    )
    bridge.startup()

    # Create an intent and manually put it in outcome_unknown.
    mgr = bridge.intent_manager
    intent = mgr.create(
        action_type="iam.grant_role",
        action_params={"subject": "alice", "role": "viewer"},
        target_type="iam",
        target_id=iam_stub.config.resource_id,
        requested_execution_mode="resource_owned",
        requester_subject="bob",
        requester_agent_id="admin-bot",
    )
    # Manually advance to outcome_unknown (simulating a prior timeout).
    mgr.transition(intent.intent_id, IntentLifecycle.EVALUATING)
    mgr.transition(intent.intent_id, IntentLifecycle.AUTHORISED)
    proof_id = "proof_recon_1"
    mgr.link_proof(intent.intent_id, proof_id)
    mgr.transition(intent.intent_id, IntentLifecycle.PROOF_ISSUED)
    mgr.transition(intent.intent_id, IntentLifecycle.SUBMITTED)
    mgr.transition(intent.intent_id, IntentLifecycle.OUTCOME_UNKNOWN)

    # Run one reconciliation pass.
    asyncio.run(bridge._reconcile_once())

    # The intent should have advanced to succeeded.
    fetched = mgr.store.get(intent.intent_id)
    assert fetched is not None
    assert fetched.lifecycle_state == IntentLifecycle.SUCCEEDED

    bridge.shutdown()


def test_reconcile_skips_intent_without_proof(database, resource_service, iam_stub, tmp_path):
    """The reconciliation worker skips intents without a linked proof
    (cannot re-submit without one)."""
    bridge = PermitGatewayBridge(
        database=database,
        resource_owned_service=resource_service,
        permit_state_path=str(tmp_path / "permit_state.db"),
        run_worker=False,
    )
    bridge.startup()

    mgr = bridge.intent_manager
    intent = mgr.create(
        action_type="iam.grant_role",
        action_params={"subject": "alice", "role": "viewer"},
        target_type="iam",
        target_id=iam_stub.config.resource_id,
        requested_execution_mode="resource_owned",
        requester_subject="bob",
        requester_agent_id="admin-bot",
    )
    # Advance to outcome_unknown WITHOUT linking a proof.
    mgr.transition(intent.intent_id, IntentLifecycle.EVALUATING)
    mgr.transition(intent.intent_id, IntentLifecycle.AUTHORISED)
    mgr.transition(intent.intent_id, IntentLifecycle.PROOF_ISSUED)
    mgr.transition(intent.intent_id, IntentLifecycle.SUBMITTED)
    mgr.transition(intent.intent_id, IntentLifecycle.OUTCOME_UNKNOWN)

    # Run reconciliation — should skip (no proof).
    asyncio.run(bridge._reconcile_once())

    fetched = mgr.store.get(intent.intent_id)
    assert fetched is not None
    # Still outcome_unknown — not advanced.
    assert fetched.lifecycle_state == IntentLifecycle.OUTCOME_UNKNOWN

    bridge.shutdown()


def test_reconcile_skips_intent_without_registered_client(database, iam_stub, tmp_path):
    """The reconciliation worker skips intents whose target_id has no
    registered resource client."""
    # Build a resource service with NO endpoints.
    svc = ResourceOwnedExecutionService()
    bridge = PermitGatewayBridge(
        database=database,
        resource_owned_service=svc,
        permit_state_path=str(tmp_path / "permit_state.db"),
        run_worker=False,
    )
    bridge.startup()

    mgr = bridge.intent_manager
    intent = mgr.create(
        action_type="iam.grant_role",
        action_params={"subject": "alice", "role": "viewer"},
        target_type="iam",
        target_id="not-registered",
        requested_execution_mode="resource_owned",
        requester_subject="bob",
        requester_agent_id="admin-bot",
    )
    mgr.transition(intent.intent_id, IntentLifecycle.EVALUATING)
    mgr.transition(intent.intent_id, IntentLifecycle.AUTHORISED)
    mgr.link_proof(intent.intent_id, "proof_x")
    mgr.transition(intent.intent_id, IntentLifecycle.PROOF_ISSUED)
    mgr.transition(intent.intent_id, IntentLifecycle.SUBMITTED)
    mgr.transition(intent.intent_id, IntentLifecycle.OUTCOME_UNKNOWN)

    # Run reconciliation — should skip (no client).
    asyncio.run(bridge._reconcile_once())

    fetched = mgr.store.get(intent.intent_id)
    assert fetched is not None
    assert fetched.lifecycle_state == IntentLifecycle.OUTCOME_UNKNOWN

    bridge.shutdown()


# ---------------------------------------------------------------------------
# 4. Bridge startup + shutdown lifecycle
# ---------------------------------------------------------------------------


def test_bridge_startup_creates_gateway(database, resource_service, tmp_path):
    bridge = PermitGatewayBridge(
        database=database,
        resource_owned_service=resource_service,
        permit_state_path=str(tmp_path / "permit_state.db"),
        run_worker=False,
    )
    assert bridge._gateway is None
    bridge.startup()
    assert bridge._gateway is not None
    bridge.shutdown()


def test_bridge_gateway_property_raises_before_startup(database, resource_service, tmp_path):
    bridge = PermitGatewayBridge(
        database=database,
        resource_owned_service=resource_service,
        permit_state_path=str(tmp_path / "permit_state.db"),
        run_worker=False,
    )
    with pytest.raises(RuntimeError, match="not started"):
        _ = bridge.gateway


# ---------------------------------------------------------------------------
# 5. Multiple resource endpoints
# ---------------------------------------------------------------------------


def test_bridge_registers_multiple_resource_clients(database, iam_stub, tmp_path):
    """When the ResourceOwnedExecutionService has multiple endpoints,
    the bridge registers a client for each."""
    svc = ResourceOwnedExecutionService()
    svc.register_endpoint(ResourceEndpointConfig(
        resource_id=iam_stub.config.resource_id,
        endpoint_url=iam_stub.endpoint_url,
        signing_key_id=iam_stub.config.signing_key_id,
        signing_key_secret=iam_stub.config.signing_key_secret,
    ))
    svc.register_endpoint(ResourceEndpointConfig(
        resource_id="other-resource",
        endpoint_url="https://other.example.invalid/submit",
        signing_key_id="other-key-1",
        signing_key_secret=b"other-secret",
    ))
    svc.authorise_tenant("tenant-acme", {iam_stub.config.resource_id, "other-resource"})

    bridge = PermitGatewayBridge(
        database=database,
        resource_owned_service=svc,
        permit_state_path=str(tmp_path / "permit_state.db"),
        run_worker=False,
    )
    bridge.startup()

    gw = bridge.gateway
    assert iam_stub.config.resource_id in gw.resource_clients
    assert "other-resource" in gw.resource_clients
    assert len(gw.resource_clients) == 2

    bridge.shutdown()
