"""Durable Cloud intent store (Prompt 10).

A Postgres-backed implementation of the Permit-side ``IntentStore``
ABC. AEIs stored here survive host failures: the Postgres database
is the canonical store, and Cloud-managed deployments take Postgres
backups as part of their normal operations.

The store uses SQLAlchemy so the same code path works against SQLite
(in tests) and Postgres (in production). The durability profile is
``durable_cloud`` — the strongest profile defined by the Permit
``DurabilityProfile`` enum.

Usage::

    from app.database import Database
    from app.services.intent_store import DurableCloudIntentStore

    db = Database(database_url="postgresql+psycopg://...")
    db.connect()
    store = DurableCloudIntentStore(db)
    mgr = IntentManager(store=store)

The store is thread-safe via SQLAlchemy's session-per-call pattern.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from actenon_permit.intent import (
    AuthorisedExecutionIntent,
    DurabilityProfile,
    IntentLifecycle,
    IntentStore,
    validate_transition,
)
from sqlalchemy import select

from app.database import Database
from app.models.intent import AuthorisedExecutionIntentRecord

logger = logging.getLogger(__name__)


class DurableCloudIntentStore(IntentStore):
    """Postgres-backed AEI store.

    Implements the Permit-side ``IntentStore`` ABC using SQLAlchemy.
    The ``database`` is a Cloud ``Database`` wrapper that produces
    short-lived SQLAlchemy sessions per call.

    The store is intentionally a thin adapter: it serialises the AEI
    to JSON for the ``body`` column, denormalises a few fields for
    indexing, and rehydrates on read. Lifecycle transition validation
    is delegated to the Permit-side ``validate_transition`` helper
    (single source of truth).
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def durability_profile(self) -> DurabilityProfile:
        return DurabilityProfile.DURABLE_CLOUD

    # ------------------------------------------------------------------
    # IntentStore ABC implementation
    # ------------------------------------------------------------------

    def put(self, intent: AuthorisedExecutionIntent) -> None:
        body = json.dumps(intent.to_dict(), default=str, sort_keys=True)
        with self._db.session() as session:
            existing = session.get(AuthorisedExecutionIntentRecord, intent.intent_id)
            if existing is None:
                record = AuthorisedExecutionIntentRecord(
                    intent_id=intent.intent_id,
                    body=body,
                    lifecycle_state=intent.lifecycle_state.value,
                    requester_subject=intent.requester_subject,
                    requester_tenant_id=intent.requester_tenant_id,
                    requested_execution_mode=intent.requested_execution_mode,
                    action_type=intent.action_type,
                    target_id=intent.target_id,
                    linked_proof_id=intent.linked_proof_id,
                    linked_receipt_id=intent.linked_receipt_id,
                    linked_refusal_id=intent.linked_refusal_id,
                    submission_reference=intent.submission_reference,
                )
                session.add(record)
            else:
                # Update in place.
                existing.body = body
                existing.lifecycle_state = intent.lifecycle_state.value
                existing.requester_subject = intent.requester_subject
                existing.requester_tenant_id = intent.requester_tenant_id
                existing.requested_execution_mode = intent.requested_execution_mode
                existing.action_type = intent.action_type
                existing.target_id = intent.target_id
                existing.linked_proof_id = intent.linked_proof_id
                existing.linked_receipt_id = intent.linked_receipt_id
                existing.linked_refusal_id = intent.linked_refusal_id
                existing.submission_reference = intent.submission_reference
                existing.updated_at = datetime.now(UTC)
            session.commit()

    def get(self, intent_id: str) -> AuthorisedExecutionIntent | None:
        with self._db.session() as session:
            record = session.get(AuthorisedExecutionIntentRecord, intent_id)
            if record is None:
                return None
            return AuthorisedExecutionIntent.from_dict(json.loads(record.body))

    def update_state(self, intent_id: str, new_state: IntentLifecycle) -> None:
        with self._db.session() as session:
            record = session.get(AuthorisedExecutionIntentRecord, intent_id)
            if record is None:
                raise KeyError(f"intent {intent_id!r} not found")
            current = IntentLifecycle(record.lifecycle_state)
            validate_transition(current, new_state)
            record.lifecycle_state = new_state.value
            record.updated_at = datetime.now(UTC)
            # Re-read the body, update the lifecycle_state in it, and write back.
            body_dict = json.loads(record.body)
            body_dict["lifecycle_state"] = new_state.value
            record.body = json.dumps(body_dict, default=str, sort_keys=True)
            session.commit()

    def list(self, *, requester_subject: str | None = None) -> list[AuthorisedExecutionIntent]:
        with self._db.session() as session:
            if requester_subject is None:
                stmt = select(AuthorisedExecutionIntentRecord).order_by(
                    AuthorisedExecutionIntentRecord.created_at
                )
            else:
                stmt = (
                    select(AuthorisedExecutionIntentRecord)
                    .where(AuthorisedExecutionIntentRecord.requester_subject == requester_subject)
                    .order_by(AuthorisedExecutionIntentRecord.created_at)
                )
            records = session.execute(stmt).scalars().all()
            return [AuthorisedExecutionIntent.from_dict(json.loads(r.body)) for r in records]

    def delete(self, intent_id: str) -> None:
        with self._db.session() as session:
            record = session.get(AuthorisedExecutionIntentRecord, intent_id)
            if record is not None:
                session.delete(record)
                session.commit()

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def _session(self):
        """Yield a SQLAlchemy Session (deprecated; use self._db.session()).

        Kept for backward compat with callers that constructed the
        store with a ``DatabaseSession`` directly. New code should
        pass a ``Database`` to the constructor.
        """
        return self._db.session()


__all__ = ["DurableCloudIntentStore"]
