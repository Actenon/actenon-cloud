from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from actenon.verifier import (
    CounterSignatureVerificationError,
    verify_countersignature,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database import Base
from app.models import (
    CounterSigningKey,
    CounterSigningKeyStatus,
    CounterSigningLifecycleStatus,
    CounterSigningOperationStatus,
)
from app.services.countersigning import (
    KEY_APPROVAL_PERMISSION,
    KEY_PROVISION_PERMISSION,
    KEY_REVOKE_PERMISSION,
    KEY_ROTATE_PERMISSION,
    SIGN_PERMISSION,
    CounterSigningAuthorizationError,
    CounterSigningService,
    LifecycleAuthorization,
    PrincipalContext,
)
from app.services.countersigning_provider import (
    CounterSigningProviderError,
    HsmKmsCounterSigningProvider,
    ManagedKeyDescriptor,
    ManagedLifecycleResult,
    ManagedSignature,
)
from app.services.key_set_publisher import (
    AtomicFileKeySetPublisher,
    KeySetPublicationError,
    PublishedKeySet,
)


@dataclass
class MutableClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


class ThrowawayHsmKmsClient:
    """Test-only custody fixture. Private keys never cross this client boundary."""

    def __init__(self) -> None:
        self._keys: dict[str, Ed25519PrivateKey] = {}
        self.sign_calls: list[str] = []
        self.disabled: set[str] = set()

    def create_non_exportable_ed25519_key(
        self,
        *,
        key_id: str,
        idempotency_token: str,
        labels: Mapping[str, str],
    ) -> ManagedKeyDescriptor:
        del labels
        provider_ref = f"test-hsm://counter-signing/{key_id}"
        private_key = self._keys.setdefault(provider_ref, Ed25519PrivateKey.generate())
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        public_key_jwk = {
            "kty": "OKP",
            "crv": "Ed25519",
            "kid": key_id,
            "alg": "EdDSA",
            "use": "sig",
            "x": base64.urlsafe_b64encode(public_bytes).decode("ascii").rstrip("="),
        }
        return ManagedKeyDescriptor(
            key_id=key_id,
            provider_key_ref=provider_ref,
            public_key_jwk=public_key_jwk,
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
        if provider_key_ref in self.disabled:
            raise RuntimeError("test HSM key disabled")
        self.sign_calls.append(provider_key_ref)
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
        assert reason
        self.disabled.add(provider_key_ref)
        return ManagedLifecycleResult(
            provider_operation_ref=f"test-hsm-disable:{idempotency_token}"
        )


class ExportingKeyClient(ThrowawayHsmKmsClient):
    def create_non_exportable_ed25519_key(
        self,
        *,
        key_id: str,
        idempotency_token: str,
        labels: Mapping[str, str],
    ) -> ManagedKeyDescriptor:
        descriptor = super().create_non_exportable_ed25519_key(
            key_id=key_id,
            idempotency_token=idempotency_token,
            labels=labels,
        )
        return ManagedKeyDescriptor(
            key_id=descriptor.key_id,
            provider_key_ref=descriptor.provider_key_ref,
            public_key_jwk={**descriptor.public_key_jwk, "d": "private-material"},
            provider_operation_ref=descriptor.provider_operation_ref,
            provider_attestation_ref=descriptor.provider_attestation_ref,
            non_exportable=descriptor.non_exportable,
        )


class FailingKeySetPublisher:
    def publish(
        self,
        *,
        document: Mapping[str, object],
        version: str,
    ) -> PublishedKeySet:
        del document, version
        raise KeySetPublicationError("simulated publication outage")


def create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return Session(bind=engine, expire_on_commit=False)


def lifecycle_authorization(permission: str) -> LifecycleAuthorization:
    return LifecycleAuthorization(
        requester=PrincipalContext(
            principal_type="user",
            principal_id="security-key-manager",
            permissions=frozenset({permission}),
        ),
        approvers=(
            PrincipalContext(
                principal_type="user",
                principal_id="security-approver-a",
                permissions=frozenset({KEY_APPROVAL_PERMISSION}),
            ),
            PrincipalContext(
                principal_type="user",
                principal_id="security-approver-b",
                permissions=frozenset({KEY_APPROVAL_PERMISSION}),
            ),
        ),
    )


def signing_authority() -> PrincipalContext:
    return PrincipalContext(
        principal_type="service",
        principal_id="counter-signing-runtime",
        permissions=frozenset({SIGN_PERMISSION}),
    )


def digest(value: str) -> dict[str, str]:
    return {
        "algorithm": "sha-256",
        "canonicalization": "RFC8785-JCS",
        "value": value * 64,
    }


def build_service(
    session: Session,
    tmp_path: Path,
    *,
    client: ThrowawayHsmKmsClient,
    clock: MutableClock,
) -> CounterSigningService:
    return CounterSigningService(
        session,
        provider=HsmKmsCounterSigningProvider(client),
        key_set_publisher=AtomicFileKeySetPublisher(tmp_path / "published-keys"),
        witness={
            "type": "service",
            "id": "actenon-counter-signing-test",
            "display_name": "Actenon Counter-Signing Test",
        },
        origin="https://witness.test.example",
        clock=clock,
    )


def test_managed_counter_signatures_survive_rotation_and_verify_offline(
    tmp_path: Path,
) -> None:
    session = create_session()
    client = ThrowawayHsmKmsClient()
    clock = MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC))
    service = build_service(session, tmp_path, client=client, clock=clock)
    try:
        first_key = service.provision_initial_key(
            key_id="counter-signing-2026-06-a",
            authorization=lifecycle_authorization(KEY_PROVISION_PERMISSION),
        )
        first_outcome = service.counter_sign(
            digest("1"),
            authority=signing_authority(),
            tenant_id="tenant-001",
            receipt_id="receipt-001",
        )

        clock.advance(hours=1)
        second_key = service.rotate_key(
            new_key_id="counter-signing-2026-06-b",
            authorization=lifecycle_authorization(KEY_ROTATE_PERMISSION),
        )
        second_outcome = service.counter_sign(
            digest("2"),
            authority=signing_authority(),
            tenant_id="tenant-001",
            receipt_id="receipt-002",
        )
        published_keys = service.current_public_key_set()

        verified_old = verify_countersignature(
            digest("1"),
            first_outcome.artifact,
            published_keys,
        )
        verified_new = verify_countersignature(
            digest("2"),
            second_outcome.artifact,
            published_keys,
        )

        assert verified_old.key_id == first_key.key_id
        assert verified_new.key_id == second_key.key_id
        assert [key["key_id"] for key in published_keys["keys"]] == [
            first_key.key_id,
            second_key.key_id,
        ]
        assert [key["status"] for key in published_keys["keys"]] == [
            "retired",
            "active",
        ]
        assert session.get(CounterSigningKey, first_key.key_id).status == (
            CounterSigningKeyStatus.retired
        )
        assert session.get(CounterSigningKey, second_key.key_id).status == (
            CounterSigningKeyStatus.active
        )

        with pytest.raises(
            CounterSignatureVerificationError,
            match="RECEIPT_DIGEST_MISMATCH",
        ):
            verify_countersignature(
                digest("3"),
                first_outcome.artifact,
                published_keys,
            )

        operations = service.list_signing_operations()
        assert [operation.status for operation in operations] == [
            CounterSigningOperationStatus.completed,
            CounterSigningOperationStatus.completed,
        ]
        assert all(operation.provider_operation_ref for operation in operations)
        lifecycle_records = service.list_lifecycle_operations()
        assert [record.status for record in lifecycle_records] == [
            CounterSigningLifecycleStatus.completed,
            CounterSigningLifecycleStatus.completed,
        ]

        current_key_set_path = (
            tmp_path / "published-keys" / ".well-known" / "actenon" / "keys.json"
        )
        assert json.loads(current_key_set_path.read_text(encoding="utf-8")) == published_keys
        assert all("d" not in key["public_key_jwk"] for key in published_keys["keys"])
        assert "private" not in json.dumps(published_keys).lower()
    finally:
        session.close()


def test_human_signing_access_is_denied_and_audited(tmp_path: Path) -> None:
    session = create_session()
    client = ThrowawayHsmKmsClient()
    clock = MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC))
    service = build_service(session, tmp_path, client=client, clock=clock)
    try:
        service.provision_initial_key(
            key_id="counter-signing-access-test",
            authorization=lifecycle_authorization(KEY_PROVISION_PERMISSION),
        )
        human = PrincipalContext(
            principal_type="user",
            principal_id="platform-admin",
            permissions=frozenset({SIGN_PERMISSION}),
        )

        with pytest.raises(CounterSigningAuthorizationError):
            service.counter_sign(digest("4"), authority=human)

        assert client.sign_calls == []
        operations = service.list_signing_operations()
        assert len(operations) == 1
        assert operations[0].status == CounterSigningOperationStatus.denied
        assert operations[0].actor_principal_id == "platform-admin"
    finally:
        session.close()


def test_compromised_historical_key_is_revoked_without_losing_prior_verification(
    tmp_path: Path,
) -> None:
    session = create_session()
    client = ThrowawayHsmKmsClient()
    clock = MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC))
    service = build_service(session, tmp_path, client=client, clock=clock)
    try:
        first_key = service.provision_initial_key(
            key_id="counter-signing-recovery-a",
            authorization=lifecycle_authorization(KEY_PROVISION_PERMISSION),
        )
        before_compromise = service.counter_sign(
            digest("5"),
            authority=signing_authority(),
        )
        clock.advance(minutes=15)
        service.rotate_key(
            new_key_id="counter-signing-recovery-b",
            authorization=lifecycle_authorization(KEY_ROTATE_PERMISSION),
        )
        clock.advance(minutes=15)
        revoked = service.revoke_key(
            key_id=first_key.key_id,
            reason="recovery drill: simulated key compromise",
            authorization=lifecycle_authorization(KEY_REVOKE_PERMISSION),
        )
        published_keys = service.current_public_key_set()

        assert revoked.status == CounterSigningKeyStatus.revoked
        assert revoked.provider_key_ref in client.disabled
        assert verify_countersignature(
            digest("5"),
            before_compromise.artifact,
            published_keys,
        ).key_id == first_key.key_id
        historical_descriptor = published_keys["keys"][0]
        assert historical_descriptor["status"] == "retired"
        assert historical_descriptor["revoked_at"]
        assert historical_descriptor["revocation_reason"]
    finally:
        session.close()


def test_key_lifecycle_requires_separation_and_two_independent_approvers(
    tmp_path: Path,
) -> None:
    session = create_session()
    client = ThrowawayHsmKmsClient()
    service = build_service(
        session,
        tmp_path,
        client=client,
        clock=MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC)),
    )
    requester = PrincipalContext(
        principal_type="user",
        principal_id="same-person",
        permissions=frozenset({KEY_PROVISION_PERMISSION, KEY_APPROVAL_PERMISSION}),
    )
    try:
        with pytest.raises(CounterSigningAuthorizationError):
            service.provision_initial_key(
                key_id="counter-signing-denied",
                authorization=LifecycleAuthorization(
                    requester=requester,
                    approvers=(requester,),
                ),
            )

        assert client._keys == {}
        records = service.list_lifecycle_operations()
        assert len(records) == 1
        assert records[0].status == CounterSigningLifecycleStatus.denied
    finally:
        session.close()


def test_provider_response_with_private_key_material_is_rejected() -> None:
    provider = HsmKmsCounterSigningProvider(ExportingKeyClient())

    with pytest.raises(CounterSigningProviderError, match="private key material"):
        provider.provision_key(
            key_id="counter-signing-private-material",
            idempotency_token="operation-001",  # noqa: S106
            labels={"actenon-purpose": "receipt_countersignature"},
        )


def test_publication_failure_does_not_activate_key_and_is_audited() -> None:
    session = create_session()
    client = ThrowawayHsmKmsClient()
    service = CounterSigningService(
        session,
        provider=HsmKmsCounterSigningProvider(client),
        key_set_publisher=FailingKeySetPublisher(),
        witness={"type": "service", "id": "actenon-counter-signing-test"},
        origin="https://witness.test.example",
        clock=MutableClock(datetime(2026, 6, 6, 12, 0, tzinfo=UTC)),
    )
    try:
        with pytest.raises(KeySetPublicationError, match="publication outage"):
            service.provision_initial_key(
                key_id="counter-signing-publication-failure",
                authorization=lifecycle_authorization(KEY_PROVISION_PERMISSION),
            )

        assert list(session.scalars(select(CounterSigningKey))) == []
        records = service.list_lifecycle_operations()
        assert len(records) == 1
        assert records[0].status == CounterSigningLifecycleStatus.failed
        assert records[0].error_code == "KEY_PROVISION_OR_PUBLICATION_FAILED"
    finally:
        session.close()
