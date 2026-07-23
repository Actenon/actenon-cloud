"""SQLAlchemy model for AuthorisedExecutionIntent (Prompt 10).

This table stores the developer-facing AEI transactions in the Cloud's
Postgres database. It is separate from the existing
``action_intent_records`` table (which is the Cloud's internal
intent model for the action control plane). The AEI is the
developer-facing surface; the action_intent_record is the internal
control-plane record.

The AEI table is the ``durable_cloud`` profile backing store for the
Permit-side ``IntentStore`` ABC (see ``app.services.intent_store``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AuthorisedExecutionIntentRecord(Base):
    """Durable record for an AuthorisedExecutionIntent (Prompt 10).

    The ``body`` column holds the full AEI JSON (as serialised by
    ``AuthorisedExecutionIntent.to_dict()``). The other columns are
    denormalised for indexing (lifecycle_state, requester_subject,
    created_at) so we can list/filter without parsing every row.

    The AEI is NOT the proof and is NOT verified by the Kernel. The
    proof (PCCB) is the boundary artefact; the AEI is the
    developer-facing transaction that may result in a proof being
    minted. The ``linked_proof_id`` column references the PCCB that
    was minted for this intent.
    """

    __tablename__ = "authorised_execution_intents"
    __table_args__ = (
        Index(
            "ix_aei_requester_subject_created_at",
            "requester_subject",
            "created_at",
        ),
        Index(
            "ix_aei_lifecycle_state",
            "lifecycle_state",
        ),
    )

    intent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    requester_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    linked_proof_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_receipt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_refusal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submission_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    # Optional version column for optimistic concurrency (future use).
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


__all__ = ["AuthorisedExecutionIntentRecord"]
