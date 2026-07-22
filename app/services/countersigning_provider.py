from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


class CounterSigningProviderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ManagedKeyDescriptor:
    key_id: str
    provider_key_ref: str
    public_key_jwk: Mapping[str, Any]
    provider_operation_ref: str
    provider_attestation_ref: str | None
    non_exportable: bool


@dataclass(frozen=True, slots=True)
class ManagedSignature:
    signature: bytes
    provider_operation_ref: str


@dataclass(frozen=True, slots=True)
class ManagedLifecycleResult:
    provider_operation_ref: str


class ManagedCounterSigningProvider(Protocol):
    def provision_key(
        self,
        *,
        key_id: str,
        idempotency_token: str,
        labels: Mapping[str, str],
    ) -> ManagedKeyDescriptor: ...

    def sign(
        self,
        *,
        provider_key_ref: str,
        message: bytes,
        idempotency_token: str,
    ) -> ManagedSignature: ...

    def disable_key(
        self,
        *,
        provider_key_ref: str,
        reason: str,
        idempotency_token: str,
    ) -> ManagedLifecycleResult: ...


class NonExportableEd25519Client(Protocol):
    """Narrow provider SDK surface that never exposes a private-key export operation."""

    def create_non_exportable_ed25519_key(
        self,
        *,
        key_id: str,
        idempotency_token: str,
        labels: Mapping[str, str],
    ) -> ManagedKeyDescriptor: ...

    def sign_ed25519(
        self,
        *,
        provider_key_ref: str,
        message: bytes,
        idempotency_token: str,
    ) -> ManagedSignature: ...

    def disable_key(
        self,
        *,
        provider_key_ref: str,
        reason: str,
        idempotency_token: str,
    ) -> ManagedLifecycleResult: ...


class HsmKmsCounterSigningProvider:
    """Adapter for an HSM/KMS client with non-exportable Ed25519 keys."""

    _PRIVATE_JWK_FIELDS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth", "k"})

    def __init__(self, client: NonExportableEd25519Client) -> None:
        self._client = client

    def provision_key(
        self,
        *,
        key_id: str,
        idempotency_token: str,
        labels: Mapping[str, str],
    ) -> ManagedKeyDescriptor:
        descriptor = self._client.create_non_exportable_ed25519_key(
            key_id=key_id,
            idempotency_token=idempotency_token,
            labels=labels,
        )
        self._validate_descriptor(descriptor, expected_key_id=key_id)
        return descriptor

    def sign(
        self,
        *,
        provider_key_ref: str,
        message: bytes,
        idempotency_token: str,
    ) -> ManagedSignature:
        if not message:
            raise CounterSigningProviderError("refusing to sign an empty counter-signature input")
        outcome = self._client.sign_ed25519(
            provider_key_ref=provider_key_ref,
            message=message,
            idempotency_token=idempotency_token,
        )
        if len(outcome.signature) != 64:
            raise CounterSigningProviderError(
                "managed provider returned an invalid Ed25519 signature length"
            )
        if not outcome.provider_operation_ref:
            raise CounterSigningProviderError(
                "managed provider did not return an operation reference"
            )
        return outcome

    def disable_key(
        self,
        *,
        provider_key_ref: str,
        reason: str,
        idempotency_token: str,
    ) -> ManagedLifecycleResult:
        outcome = self._client.disable_key(
            provider_key_ref=provider_key_ref,
            reason=reason,
            idempotency_token=idempotency_token,
        )
        if not outcome.provider_operation_ref:
            raise CounterSigningProviderError(
                "managed provider did not return a disable operation reference"
            )
        return outcome

    def _validate_descriptor(
        self,
        descriptor: ManagedKeyDescriptor,
        *,
        expected_key_id: str,
    ) -> None:
        if descriptor.key_id != expected_key_id:
            raise CounterSigningProviderError(
                "managed provider returned a key_id that differs from the requested kid"
            )
        if not descriptor.non_exportable:
            raise CounterSigningProviderError(
                "counter-signing keys must be provider-enforced non-exportable keys"
            )
        if not descriptor.provider_key_ref or not descriptor.provider_operation_ref:
            raise CounterSigningProviderError(
                "managed provider must return key and operation references"
            )

        jwk = dict(descriptor.public_key_jwk)
        if self._PRIVATE_JWK_FIELDS.intersection(jwk):
            raise CounterSigningProviderError(
                "managed provider response included private key material"
            )
        if (
            jwk.get("kty") != "OKP"
            or jwk.get("crv") != "Ed25519"
            or jwk.get("kid") not in (None, expected_key_id)
            or jwk.get("alg") not in (None, "EdDSA")
            or jwk.get("use") not in (None, "sig")
        ):
            raise CounterSigningProviderError(
                "managed provider must return a public Ed25519 OKP JWK for the requested kid"
            )
        public_value = jwk.get("x")
        if not isinstance(public_value, str) or len(self._decode_base64url(public_value)) != 32:
            raise CounterSigningProviderError(
                "managed provider returned an invalid Ed25519 public key"
            )

    @staticmethod
    def _decode_base64url(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        try:
            return base64.b64decode(
                value.translate(str.maketrans("-_", "+/")) + padding,
                validate=True,
            )
        except (binascii.Error, ValueError) as exc:
            raise CounterSigningProviderError(
                "managed provider returned malformed base64url public key material"
            ) from exc


__all__ = [
    "CounterSigningProviderError",
    "HsmKmsCounterSigningProvider",
    "ManagedCounterSigningProvider",
    "ManagedKeyDescriptor",
    "ManagedLifecycleResult",
    "ManagedSignature",
    "NonExportableEd25519Client",
]
