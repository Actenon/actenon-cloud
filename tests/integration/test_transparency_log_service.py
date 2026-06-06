from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from actenon.verifier import (
    TransparencyVerificationError,
    verify_checkpoint_signature,
    verify_consistency,
    verify_countersignature,
    verify_countersignature_inclusion,
    verify_inclusion,
    verify_monitor_update,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database import Base
from app.models import TransparencyIntegrityEvent, TransparencyLogLeaf
from app.services.countersigning import (
    CHECKPOINT_SIGN_PERMISSION,
    KEY_APPROVAL_PERMISSION,
    KEY_PROVISION_PERMISSION,
    KEY_ROTATE_PERMISSION,
    SIGN_PERMISSION,
    CounterSigningService,
    LifecycleAuthorization,
    PrincipalContext,
)
from app.services.countersigning_provider import (
    HsmKmsCounterSigningProvider,
    ManagedKeyDescriptor,
    ManagedLifecycleResult,
    ManagedSignature,
)
from app.services.key_set_publisher import AtomicFileKeySetPublisher
from app.services.transparency_format import (
    build_checkpoint_artifact,
    build_checkpoint_statement,
)
from app.services.transparency_log import (
    CounterSigningCheckpointSigner,
    TransparencyActor,
    TransparencyLogService,
)


@dataclass
class MutableClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


class ThrowawayManagedKeyClient:
    """Test-only HSM fixture; callers can request signatures but cannot export keys."""

    def __init__(self) -> None:
        self._keys: dict[str, Ed25519PrivateKey] = {}

    def create_non_exportable_ed25519_key(
        self,
        *,
        key_id: str,
        idempotency_token: str,
        labels: Mapping[str, str],
    ) -> ManagedKeyDescriptor:
        del labels
        provider_ref = f"test-hsm://transparency/{key_id}"
        private_key = self._keys.setdefault(provider_ref, Ed25519PrivateKey.generate())
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return ManagedKeyDescriptor(
            key_id=key_id,
            provider_key_ref=provider_ref,
            public_key_jwk={
                "kty": "OKP",
                "crv": "Ed25519",
                "kid": key_id,
                "alg": "EdDSA",
                "use": "sig",
                "x": base64.urlsafe_b64encode(public_bytes)
                .decode("ascii")
                .rstrip("="),
            },
            provider_operation_ref=f"test-hsm-create:{idempotency_token}",
            provider_attestation_ref=f"test-hsm-attestation:{key_id}",
            non_exportable=True,
        )

    def sign_ed25519(
        self,
        *,
        provider_key_ref: str,
        message: bytes,
        idempotency_token: str,
    ) -> ManagedSignature:
        return ManagedSignature(
            signature=self._keys[provider_key_ref].sign(message),
            provider_operation_ref=f"test-hsm-sign:{idempotency_token}",
        )

    def disable_key(
        self,
        *,
        provider_key_ref: str,
        reason: str,
        idempotency_token: str,
    ) -> ManagedLifecycleResult:
        del provider_key_ref, reason
        return ManagedLifecycleResult(
            provider_operation_ref=f"test-hsm-disable:{idempotency_token}"
        )


def digest(number: int) -> dict[str, str]:
    return {
        "algorithm": "sha-256",
        "canonicalization": "RFC8785-JCS",
        "value": f"{number:064x}",
    }


def lifecycle_authorization(
    permission: str = KEY_PROVISION_PERMISSION,
) -> LifecycleAuthorization:
    return LifecycleAuthorization(
        requester=PrincipalContext(
            principal_type="user",
            principal_id="key-manager",
            permissions=frozenset({permission}),
        ),
        approvers=(
            PrincipalContext(
                principal_type="user",
                principal_id="approver-a",
                permissions=frozenset({KEY_APPROVAL_PERMISSION}),
            ),
            PrincipalContext(
                principal_type="user",
                principal_id="approver-b",
                permissions=frozenset({KEY_APPROVAL_PERMISSION}),
            ),
        ),
    )


def build_services(
    tmp_path: Path,
) -> tuple[
    Session,
    MutableClock,
    CounterSigningService,
    CounterSigningCheckpointSigner,
    TransparencyLogService,
]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'transparency.db'}")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine, expire_on_commit=False)
    clock = MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC))
    custody = CounterSigningService(
        session,
        provider=HsmKmsCounterSigningProvider(ThrowawayManagedKeyClient()),
        key_set_publisher=AtomicFileKeySetPublisher(tmp_path / "published-keys"),
        witness={
            "type": "service",
            "id": "actenon-transparency-test",
            "display_name": "Actenon Transparency Test",
        },
        origin="https://transparency.test.example",
        clock=clock,
    )
    custody.provision_initial_key(
        key_id="transparency-2026-06-a",
        authorization=lifecycle_authorization(),
    )
    signer = CounterSigningCheckpointSigner(
        custody,
        authority=PrincipalContext(
            principal_type="service",
            principal_id="transparency-checkpoint-runtime",
            permissions=frozenset({CHECKPOINT_SIGN_PERMISSION}),
        ),
    )
    log = TransparencyLogService(
        session,
        log_identity=custody.witness,
        checkpoint_signer=signer,
        clock=clock,
    )
    return session, clock, custody, signer, log


def test_transparency_log_proofs_verify_with_public_sdk(tmp_path: Path) -> None:
    session, clock, custody, _, log = build_services(tmp_path)
    try:
        for number in (1, 2):
            log.append_receipt_digest(digest(number))
        old = log.publish_checkpoint(
            actor=TransparencyActor("service", "checkpoint-publisher")
        )

        clock.advance(minutes=1)
        for number in (3, 4):
            log.append_receipt_digest(digest(number))
        new = log.publish_checkpoint(
            actor=TransparencyActor("service", "checkpoint-publisher")
        )

        inclusion, inclusion_checkpoint = log.inclusion_proof(digest(3))
        consistency, old_checkpoint, new_checkpoint = log.consistency_proof(
            old_tree_size=2,
            new_tree_size=4,
        )
        monitor_update = log.monitor_update(previous_tree_size=2)
        trusted_keys = custody.current_public_key_set()

        assert old.checkpoint == old_checkpoint
        assert new.checkpoint == new_checkpoint
        assert verify_checkpoint_signature(old_checkpoint, trusted_keys).tree_size == 2
        assert verify_checkpoint_signature(new_checkpoint, trusted_keys).tree_size == 4
        assert verify_inclusion(
            digest(3),
            inclusion,
            inclusion_checkpoint,
        ).leaf_index == 2
        verified_consistency = verify_consistency(
            old_checkpoint,
            new_checkpoint,
            consistency,
        )
        assert (verified_consistency.old_tree_size, verified_consistency.new_tree_size) == (
            2,
            4,
        )
        assert verify_monitor_update(
            monitor_update["previous_checkpoint"],
            monitor_update["current_checkpoint"],
            monitor_update["consistency_proof"],
            trusted_keys,
        ).current.tree_size == 4
        assert log.audit_integrity().ok is True

        leaves = list(session.scalars(select(TransparencyLogLeaf)))
        assert [leaf.receipt_digest for leaf in leaves] == [
            digest(number)["value"] for number in (1, 2, 3, 4)
        ]
        assert all(not hasattr(leaf, "receipt_payload") for leaf in leaves)
        assert all(not hasattr(leaf, "tenant_id") for leaf in leaves)
    finally:
        session.close()


def test_countersignature_anchor_is_verifiable_and_orphans_are_rejected(
    tmp_path: Path,
) -> None:
    session, _, custody, _, log = build_services(tmp_path)
    try:
        for number in (1, 2, 3):
            log.append_receipt_digest(digest(number))
        checkpoint = log.publish_checkpoint(
            actor=TransparencyActor("service", "checkpoint-publisher")
        ).checkpoint
        proof, _ = log.inclusion_proof(digest(3))
        countersignature = custody.counter_sign(
            digest(3),
            authority=PrincipalContext(
                principal_type="service",
                principal_id="counter-signing-runtime",
                permissions=frozenset({SIGN_PERMISSION}),
            ),
            anchor_reference={
                "type": "transparency_log",
                "id": log.log_id,
                "leaf_index": 2,
            },
        ).artifact
        trusted_keys = custody.current_public_key_set()

        verify_countersignature(digest(3), countersignature, trusted_keys)
        anchored = verify_countersignature_inclusion(
            countersignature,
            proof,
            checkpoint,
            trusted_keys,
        )
        assert anchored.leaf_index == 2

        orphan = {
            **countersignature,
            "anchor_reference": {
                "type": "transparency_log",
                "id": log.log_id,
                "leaf_index": 1,
            },
        }
        with pytest.raises(TransparencyVerificationError) as raised:
            verify_countersignature_inclusion(
                orphan,
                proof,
                checkpoint,
                trusted_keys,
            )
        assert raised.value.code == "ORPHAN_COUNTERSIGNATURE"
    finally:
        session.close()


def test_checkpoint_kid_rotates_without_invalidating_history(tmp_path: Path) -> None:
    session, clock, custody, _, log = build_services(tmp_path)
    try:
        log.append_receipt_digest(digest(1))
        first = log.publish_checkpoint(
            actor=TransparencyActor("service", "checkpoint-publisher")
        ).checkpoint

        clock.advance(hours=1)
        custody.rotate_key(
            new_key_id="transparency-2026-06-b",
            authorization=lifecycle_authorization(KEY_ROTATE_PERMISSION),
        )
        log.append_receipt_digest(digest(2))
        second = log.publish_checkpoint(
            actor=TransparencyActor("service", "checkpoint-publisher")
        ).checkpoint
        trusted_keys = custody.current_public_key_set()

        assert first["signature"]["key_id"] == "transparency-2026-06-a"
        assert second["signature"]["key_id"] == "transparency-2026-06-b"
        assert verify_checkpoint_signature(first, trusted_keys).tree_size == 1
        assert verify_checkpoint_signature(second, trusted_keys).tree_size == 2
        assert [key["status"] for key in trusted_keys["keys"]] == [
            "retired",
            "active",
        ]
    finally:
        session.close()


def test_signed_fork_and_rewind_are_detectable_by_public_verifier(
    tmp_path: Path,
) -> None:
    session, clock, custody, signer, log = build_services(tmp_path)
    try:
        for number in (1, 2):
            log.append_receipt_digest(digest(number))
        old = log.publish_checkpoint(
            actor=TransparencyActor("service", "checkpoint-publisher")
        ).checkpoint
        clock.advance(minutes=1)
        for number in (3, 4):
            log.append_receipt_digest(digest(number))
        current = log.publish_checkpoint(
            actor=TransparencyActor("service", "checkpoint-publisher")
        ).checkpoint

        fork_statement = build_checkpoint_statement(
            log_identity=custody.witness,
            tree_size=4,
            root_hash="f" * 64,
            issued_at=clock(),
        )
        fork_signature = signer.sign(
            fork_statement,
            idempotency_token="forced-internal-inconsistency",  # noqa: S106
        )
        fork = build_checkpoint_artifact(
            statement=fork_statement,
            key_id=fork_signature.key_id,
            signature=fork_signature.signature,
        )
        trusted_keys = custody.current_public_key_set()
        verify_checkpoint_signature(fork, trusted_keys)

        same_size_proof = {
            "contract": {
                "name": "transparency_consistency_proof",
                "version": "v1",
            },
            "log_id": log.log_id,
            "hash_algorithm": "sha-256",
            "old_tree_size": 4,
            "new_tree_size": 4,
            "consistency_path": [],
        }
        with pytest.raises(TransparencyVerificationError) as forked:
            verify_monitor_update(current, fork, same_size_proof, trusted_keys)
        assert forked.value.code == "EQUIVOCATION_DETECTED"

        with pytest.raises(TransparencyVerificationError) as rewound:
            verify_consistency(current, old, same_size_proof)
        assert rewound.value.code == "REWIND_DETECTED"
    finally:
        session.close()


def test_internal_integrity_audit_records_digest_tampering(tmp_path: Path) -> None:
    session, _, _, _, log = build_services(tmp_path)
    try:
        log.append_receipt_digest(digest(1))
        leaf = session.scalar(select(TransparencyLogLeaf))
        assert leaf is not None
        leaf.leaf_hash = "0" * 64
        session.add(leaf)
        session.commit()

        report = log.audit_integrity()

        assert report.ok is False
        assert "LEAF_HASH_MISMATCH" in report.error_codes
        event = session.scalar(select(TransparencyIntegrityEvent))
        assert event is not None
        assert event.severity == "critical"
    finally:
        session.close()
