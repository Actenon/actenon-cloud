"""Tests for DurableCloudIntentStore (Prompt 10).

These tests use SQLite (via the Cloud ``Database`` wrapper) to verify
the store's behaviour without requiring a real Postgres. The same
code path runs against Postgres in production — the SQLAlchemy model
and store are dialect-agnostic.

Covers:
  * put + get round-trip preserves all AEI fields.
  * update_state enforces lifecycle transitions.
  * list filters by requester_subject.
  * delete removes the record.
  * persistence across Database reconnect (simulates host restart).
  * store_capabilities reports durable_cloud profile.
"""

from __future__ import annotations

import pytest
from actenon_permit.intent import (
    DurabilityProfile,
    IntentLifecycle,
    IntentManager,
    IntentTransitionError,
    store_capabilities,
)

from app.database import Base, Database
from app.models.intent import AuthorisedExecutionIntentRecord
from app.services.intent_store import DurableCloudIntentStore


@pytest.fixture
def database(tmp_path):
    """SQLite-backed Database for testing."""
    db = Database(database_url=f"sqlite+pysqlite:///{tmp_path / 'test_intents.db'}")
    db.connect()
    # Create the AEI table.
    Base.metadata.create_all(bind=db.engine, tables=[AuthorisedExecutionIntentRecord.__table__])
    yield db
    Base.metadata.drop_all(bind=db.engine, tables=[AuthorisedExecutionIntentRecord.__table__])
    db.disconnect()


@pytest.fixture
def store(database):
    return DurableCloudIntentStore(database)


@pytest.fixture
def manager(store):
    return IntentManager(store=store)


# ---------------------------------------------------------------------------
# Durability profile
# ---------------------------------------------------------------------------


def test_durability_profile_is_durable_cloud(store):
    """The Cloud store reports the strongest durability profile."""
    assert store.durability_profile == DurabilityProfile.DURABLE_CLOUD


def test_store_capabilities_report_host_failure_survival(store):
    """durable_cloud reports survives_host_failure=True (the whole point
    of the Cloud store — Postgres + backups)."""
    caps = store_capabilities(store)
    assert caps["durability_profile"] == "durable_cloud"
    assert caps["survives_process_restart"] is True
    assert caps["survives_host_failure"] is True
    assert caps["pollable_after_process_termination"] is True


# ---------------------------------------------------------------------------
# put + get round-trip
# ---------------------------------------------------------------------------


def test_put_then_get_preserves_all_fields(manager, store):
    """An AEI written via the manager is readable via the store with
    all fields preserved."""
    intent = manager.create(
        action_type="issue.create",
        action_params={"owner": "actenon", "repo": "demo", "title": "via cloud"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
        requester_tenant_id="tenant-acme",
        metadata={"correlation_id": "abc-123"},
    )
    fetched = store.get(intent.intent_id)
    assert fetched is not None
    assert fetched.intent_id == intent.intent_id
    assert fetched.action_type == "issue.create"
    assert fetched.action_params == {"owner": "actenon", "repo": "demo", "title": "via cloud"}
    assert fetched.requester_subject == "alice"
    assert fetched.requester_tenant_id == "tenant-acme"
    assert fetched.metadata == {"correlation_id": "abc-123"}
    assert fetched.lifecycle_state == IntentLifecycle.CREATED


def test_get_returns_none_for_unknown(store):
    assert store.get("intent_doesnotexist") is None


# ---------------------------------------------------------------------------
# update_state + lifecycle transitions
# ---------------------------------------------------------------------------


def test_update_state_transitions_lifecycle(manager, store):
    """update_state writes the new lifecycle to both the denormalised
    column and the JSON body, and re-reads correctly."""
    intent = manager.create(
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
    )
    store.update_state(intent.intent_id, IntentLifecycle.EVALUATING)
    fetched = store.get(intent.intent_id)
    assert fetched is not None
    assert fetched.lifecycle_state == IntentLifecycle.EVALUATING


def test_update_state_rejects_illegal_transition(manager, store):
    """Illegal transitions raise IntentTransitionError and do NOT mutate
    the stored record."""
    intent = manager.create(
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
    )
    with pytest.raises(IntentTransitionError):
        store.update_state(intent.intent_id, IntentLifecycle.SUCCEEDED)
    # State is unchanged.
    fetched = store.get(intent.intent_id)
    assert fetched is not None
    assert fetched.lifecycle_state == IntentLifecycle.CREATED


def test_update_state_unknown_intent_raises(store):
    with pytest.raises(KeyError):
        store.update_state("intent_unknown", IntentLifecycle.EVALUATING)


# ---------------------------------------------------------------------------
# list + filter
# ---------------------------------------------------------------------------


def test_list_returns_all_intents(manager, store):
    manager.create(
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t1"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
    )
    manager.create(
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t2"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="bob",
        requester_agent_id="bot",
    )
    all_intents = store.list()
    assert len(all_intents) == 2


def test_list_filtered_by_subject(manager, store):
    manager.create(
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t1"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
    )
    manager.create(
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t2"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="bob",
        requester_agent_id="bot",
    )
    alice_intents = store.list(requester_subject="alice")
    assert len(alice_intents) == 1
    assert alice_intents[0].requester_subject == "alice"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_removes_record(manager, store):
    intent = manager.create(
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
    )
    assert store.get(intent.intent_id) is not None
    store.delete(intent.intent_id)
    assert store.get(intent.intent_id) is None


def test_delete_unknown_intent_is_noop(store):
    store.delete("intent_doesnotexist")  # no raise


# ---------------------------------------------------------------------------
# Persistence across Database reconnect (simulates host restart)
# ---------------------------------------------------------------------------


def test_intents_survive_database_reconnect(tmp_path):
    """AEIs written to the Cloud store survive a Database disconnect +
    reconnect. This is the host-failure survival guarantee."""
    db_path = str(tmp_path / "persist_intents.db")

    # First session: write an intent.
    db1 = Database(database_url=f"sqlite+pysqlite:///{db_path}")
    db1.connect()
    Base.metadata.create_all(bind=db1.engine, tables=[AuthorisedExecutionIntentRecord.__table__])
    store1 = DurableCloudIntentStore(db1)
    mgr1 = IntentManager(store=store1)
    intent = mgr1.create(
        action_type="issue.create",
        action_params={"owner": "actenon", "repo": "demo", "title": "persist me"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
    )
    # Advance the lifecycle so we can verify state is preserved too.
    store1.update_state(intent.intent_id, IntentLifecycle.EVALUATING)
    db1.disconnect()

    # Second session: the intent is still there.
    db2 = Database(database_url=f"sqlite+pysqlite:///{db_path}")
    db2.connect()
    store2 = DurableCloudIntentStore(db2)
    fetched = store2.get(intent.intent_id)
    assert fetched is not None
    assert fetched.action_type == "issue.create"
    assert fetched.action_params == {"owner": "actenon", "repo": "demo", "title": "persist me"}
    assert fetched.lifecycle_state == IntentLifecycle.EVALUATING
    db2.disconnect()


# ---------------------------------------------------------------------------
# Integration with IntentManager.execute_brokered
# ---------------------------------------------------------------------------


def test_manager_executes_intent_against_cloud_store(tmp_path, database):
    """IntentManager.execute_brokered works against the Cloud store.

    This proves the Cloud store plugs into the existing Prompt-10
    execution path without modification.
    """
    import os
    from datetime import UTC, datetime, timedelta

    from actenon_permit import (
        PDP,
        Broker,
        Budget,
        CredentialProviderRegistry,
        Decision,
        DecisionOutcome,
        GitHubAdapter,
        Grant,
        Ledger,
        LocalDevSecretProvider,
        Rate,
        Scopes,
        SQLiteStore,
    )

    # Build a real PDP + broker (using Permit's SQLiteStore, separate
    # from the Cloud Database).
    permit_db_path = str(tmp_path / "permit.db")
    os.environ["ACTENON_DB_PATH"] = permit_db_path
    os.environ["ACTENON_SIGNING_KEY"] = "test-signing-key-not-secret"

    permit_store = SQLiteStore(permit_db_path)
    ledger = Ledger(permit_store)
    pdp = PDP(permit_store, ledger)
    grant = Grant(
        agent_id="cloud-test-agent",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=Scopes(allow=["issue.create"]),
        budget=Budget(currency="USD", limit=10.0, remaining=10.0),
        rate=Rate(max=10, per_seconds=60),
    )
    grant.sign()
    permit_store.put_grant(grant)

    cred_registry = CredentialProviderRegistry()
    cred_registry.register(
        "GITHUB_TOKEN",
        LocalDevSecretProvider({"GITHUB_TOKEN": "ghp_test_NOT_REAL_0123456789abcdef"}),
    )
    broker = Broker(pdp, credential_providers=cred_registry, production_mode=False)
    adapter = GitHubAdapter(test_mode=True)
    decision = Decision(outcome=DecisionOutcome.ALLOW, reason="test", rule_matched="test")

    # Use the Cloud store for the intent.
    store = DurableCloudIntentStore(database)
    mgr = IntentManager(store=store)
    intent = mgr.create(
        action_type="issue.create",
        action_params={"owner": "actenon", "repo": "demo", "title": "via cloud execute"},
        target_type="github",
        target_id="github",
        requested_execution_mode="brokered",
        requester_subject="alice",
        requester_agent_id="bot",
    )
    updated, result = mgr.execute_brokered(
        intent,
        grant=grant,
        decision=decision,
        broker=broker,
        adapter=adapter,
        credential_ref="GITHUB_TOKEN",
    )
    assert updated.lifecycle_state == IntentLifecycle.SUCCEEDED
    assert result.state == "succeeded"

    # Verify the lifecycle advanced in the Cloud store too.
    fetched = store.get(intent.intent_id)
    assert fetched is not None
    assert fetched.lifecycle_state == IntentLifecycle.SUCCEEDED
    assert fetched.linked_proof_id is not None
    assert len(fetched.linked_attempt_ids) == 1
