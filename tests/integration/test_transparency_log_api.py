from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from actenon.verifier import (
    verify_checkpoint_signature,
    verify_consistency,
    verify_inclusion,
)
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.countersigning import (
    CHECKPOINT_SIGN_PERMISSION,
    CounterSigningService,
    PrincipalContext,
)
from app.services.countersigning_provider import HsmKmsCounterSigningProvider
from app.services.key_set_publisher import AtomicFileKeySetPublisher
from app.services.transparency_log import CounterSigningCheckpointSigner
from tests.integration.test_transparency_log_service import (
    MutableClock,
    ThrowawayManagedKeyClient,
    lifecycle_authorization,
)


def digest(number: int) -> dict[str, str]:
    return {
        "algorithm": "sha-256",
        "canonicalization": "RFC8785-JCS",
        "value": f"{number:064x}",
    }


@contextmanager
def configured_checkpoint_signer(
    client: TestClient,
    tmp_path: Path,
) -> Iterator[CounterSigningService]:
    engine = client.app.state.container.database.engine
    assert engine is not None
    session = Session(bind=engine, expire_on_commit=False)
    settings = client.app.state.container.settings
    clock = MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC))
    custody = CounterSigningService(
        session,
        provider=HsmKmsCounterSigningProvider(ThrowawayManagedKeyClient()),
        key_set_publisher=AtomicFileKeySetPublisher(tmp_path / "published-keys-api"),
        witness={
            "type": settings.transparency_log_identity_type,
            "id": settings.transparency_log_id,
            "display_name": settings.transparency_log_display_name,
        },
        origin="https://transparency-api.test.example",
        clock=clock,
    )
    custody.provision_initial_key(
        key_id="transparency-api-2026-06",
        authorization=lifecycle_authorization(),
    )
    client.app.state.transparency_checkpoint_signer = CounterSigningCheckpointSigner(
        custody,
        authority=PrincipalContext(
            principal_type="service",
            principal_id="transparency-api-runtime",
            permissions=frozenset({CHECKPOINT_SIGN_PERMISSION}),
        ),
    )
    try:
        yield custody
    finally:
        del client.app.state.transparency_checkpoint_signer
        session.close()


def test_transparency_api_serves_public_verifiable_proofs(
    client: TestClient,
    tmp_path: Path,
) -> None:
    log_id = client.app.state.container.settings.transparency_log_id
    with configured_checkpoint_signer(client, tmp_path) as custody:
        for number in (1, 2):
            response = client.post(
                f"/api/v1/transparency/logs/{log_id}/digests",
                json={"receipt_digest": digest(number)},
            )
            assert response.status_code == 201, response.text
        old = client.post(f"/api/v1/transparency/logs/{log_id}/checkpoints")
        assert old.status_code == 201, old.text

        for number in (3, 4):
            response = client.post(
                f"/api/v1/transparency/logs/{log_id}/digests",
                json={"receipt_digest": digest(number)},
            )
            assert response.status_code == 201, response.text
        new = client.post(f"/api/v1/transparency/logs/{log_id}/checkpoints")
        assert new.status_code == 201, new.text

        # Public witness endpoints do not require an operator token.
        headers = dict(client.headers)
        client.headers.pop("Authorization")
        try:
            inclusion = client.get(
                f"/api/v1/transparency/logs/{log_id}/proofs/inclusion",
                params={"receipt_digest": digest(3)["value"]},
            )
            consistency = client.get(
                f"/api/v1/transparency/logs/{log_id}/proofs/consistency",
                params={"old_tree_size": 2, "new_tree_size": 4},
            )
            monitor = client.get(
                f"/api/v1/transparency/logs/{log_id}/monitor",
                params={"previous_tree_size": 2},
            )
        finally:
            client.headers.update(headers)

        assert inclusion.status_code == 200, inclusion.text
        assert consistency.status_code == 200, consistency.text
        assert monitor.status_code == 200, monitor.text

        trusted_keys = custody.current_public_key_set()
        inclusion_body = inclusion.json()
        consistency_body = consistency.json()
        verify_checkpoint_signature(inclusion_body["checkpoint"], trusted_keys)
        assert verify_inclusion(
            digest(3),
            inclusion_body["proof"],
            inclusion_body["checkpoint"],
        ).leaf_index == 2
        verified = verify_consistency(
            consistency_body["old_checkpoint"],
            consistency_body["new_checkpoint"],
            consistency_body["proof"],
        )
        assert (verified.old_tree_size, verified.new_tree_size) == (2, 4)
