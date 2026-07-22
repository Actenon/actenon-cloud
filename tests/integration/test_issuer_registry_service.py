from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from actenon.verifier import (
    TrustArtifactVerificationError,
    verify_issuer_status,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database import Base
from app.models import (
    IssuerStanding,
    IssuerStatusPublicationRecord,
    IssuerStatusPublicationStatus,
)
from app.services.countersigning import (
    ISSUER_STATUS_SIGN_PERMISSION,
    KEY_PROVISION_PERMISSION,
    CounterSigningService,
    ManagedIssuerStatusSignature,
    PrincipalContext,
)
from app.services.countersigning_provider import HsmKmsCounterSigningProvider
from app.services.issuer_registry import (
    ISSUER_REGISTRY_ADMIN_PERMISSIONS,
    CounterSigningIssuerStatusSigner,
    IssuerRegistryActor,
    IssuerRegistryConfigurationError,
    IssuerRegistryService,
)
from app.services.key_set_publisher import AtomicFileKeySetPublisher
from tests.integration.test_counter_signing_service import (
    MutableClock,
    ThrowawayHsmKmsClient,
    lifecycle_authorization,
)

STATUS_AUTHORITY = {
    "type": "service",
    "id": "actenon-issuer-registry-test",
    "display_name": "Actenon Issuer Registry Test",
}
ISSUER = {
    "type": "organization",
    "id": "issuer.example.test",
    "display_name": "Example Issuer",
}


class FailingIssuerStatusSigner:
    def sign(
        self,
        statement: object,
        *,
        idempotency_token: str,
    ) -> ManagedIssuerStatusSignature:
        del statement, idempotency_token
        raise RuntimeError("simulated managed signer outage")


def create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return Session(bind=engine, expire_on_commit=False)


def registry_actor() -> IssuerRegistryActor:
    return IssuerRegistryActor(
        principal_type="user",
        principal_id="issuer-registry-admin",
        permissions=ISSUER_REGISTRY_ADMIN_PERMISSIONS,
    )


def build_services(
    session: Session,
    tmp_path: Path,
    *,
    clock: MutableClock,
) -> tuple[CounterSigningService, IssuerRegistryService]:
    custody = CounterSigningService(
        session,
        provider=HsmKmsCounterSigningProvider(ThrowawayHsmKmsClient()),
        key_set_publisher=AtomicFileKeySetPublisher(
            tmp_path / "published-issuer-status-keys"
        ),
        witness=STATUS_AUTHORITY,
        origin="https://issuer-status.test.example",
        clock=clock,
    )
    custody.provision_initial_key(
        key_id="issuer-status-2026-06",
        authorization=lifecycle_authorization(KEY_PROVISION_PERMISSION),
    )
    signer = CounterSigningIssuerStatusSigner(
        custody,
        authority=PrincipalContext(
            principal_type="service",
            principal_id="issuer-status-runtime",
            permissions=frozenset({ISSUER_STATUS_SIGN_PERMISSION}),
        ),
    )
    registry = IssuerRegistryService(
        session,
        status_authority=STATUS_AUTHORITY,
        status_signer=signer,
        clock=clock,
        artifact_ttl_seconds=300,
        max_staleness_seconds=300,
    )
    return custody, registry


def test_revocation_is_published_and_refused_by_public_verifier(
    tmp_path: Path,
) -> None:
    session = create_session()
    clock = MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC))
    custody, registry = build_services(session, tmp_path, clock=clock)
    actor = registry_actor()
    try:
        issuer = registry.register_issuer(ISSUER, actor=actor)
        good = registry.publish_status(issuer.registry_id, actor=actor)
        trusted_keys = custody.current_public_key_set()

        verified = verify_issuer_status(
            ISSUER,
            good.artifact,
            trusted_keys,
            clock(),
            max_age_seconds=300,
        )
        assert verified is not None
        assert verified.status == "good_standing"

        clock.advance(seconds=45)
        revoked = registry.revoke_issuer(
            issuer.registry_id,
            reason="issuer signing authority reported compromised",
            actor=actor,
        )
        assert revoked.issuer.standing == IssuerStanding.revoked
        assert registry.latest_status_artifact(
            registry_id=issuer.registry_id
        ) == revoked.publication.artifact

        with pytest.raises(TrustArtifactVerificationError) as refusal:
            verify_issuer_status(
                ISSUER,
                revoked.publication.artifact,
                trusted_keys,
                clock(),
                max_age_seconds=300,
            )
        assert refusal.value.code == "ISSUER_REVOKED"
        assert (
            revoked.publication.publication.expires_at
            - revoked.publication.publication.issued_at
        ).total_seconds() == 300

        events = registry.list_audit_events(issuer.registry_id)
        assert [event.event_type for event in events] == [
            "issuer.registered",
            "issuer.status_published",
            "issuer.revoked",
            "issuer.status_published",
        ]
        key = trusted_keys["keys"][0]
        assert "issuer_status" in key["use"]
    finally:
        session.close()


def test_revocation_remains_durable_when_status_signing_fails_closed(
    tmp_path: Path,
) -> None:
    session = create_session()
    clock = MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC))
    custody, registry = build_services(session, tmp_path, clock=clock)
    actor = registry_actor()
    try:
        issuer = registry.register_issuer(ISSUER, actor=actor)
        old_good = registry.publish_status(issuer.registry_id, actor=actor)
        trusted_keys = custody.current_public_key_set()

        registry.status_signer = FailingIssuerStatusSigner()
        clock.advance(seconds=30)
        with pytest.raises(
            IssuerRegistryConfigurationError,
            match="publication failed closed",
        ):
            registry.revoke_issuer(
                issuer.registry_id,
                reason="emergency revocation during signing outage",
                actor=actor,
            )

        persisted = registry.get_issuer(issuer.registry_id)
        assert persisted.standing == IssuerStanding.revoked
        with pytest.raises(
            IssuerRegistryConfigurationError,
            match="no current signed issuer-status",
        ):
            registry.latest_status_artifact(registry_id=issuer.registry_id)

        failed = session.scalar(
            select(IssuerStatusPublicationRecord).where(
                IssuerStatusPublicationRecord.issuer_registry_id
                == issuer.registry_id,
                IssuerStatusPublicationRecord.status
                == IssuerStatusPublicationStatus.failed,
            )
        )
        assert failed is not None
        assert failed.status_version == persisted.status_version

        # A relying party may have cached the old good-standing artifact, but
        # its acceptance window is bounded by the configured five-minute TTL.
        clock.advance(seconds=271)
        with pytest.raises(TrustArtifactVerificationError) as stale:
            verify_issuer_status(
                ISSUER,
                old_good.artifact,
                trusted_keys,
                clock(),
                max_age_seconds=300,
            )
        assert stale.value.code == "ISSUER_STATUS_EXPIRED"
    finally:
        session.close()
