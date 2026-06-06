from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import rfc8785

COUNTERSIGNATURE_CONTEXT = "actenon.receipt-countersignature.v1"
COUNTERSIGNATURE_CONTRACT = {
    "name": "receipt_countersignature",
    "version": "v1",
}
COUNTERSIGNATURE_KEY_USE = "receipt_countersignature"
DIGEST_ALGORITHM = "sha-256"
DIGEST_CANONICALIZATION = "RFC8785-JCS"
_HEX_256_RE = re.compile(r"^[0-9a-f]{64}$")


class CounterSignatureFormatError(ValueError):
    pass


def canonicalize_bytes(value: Any) -> bytes:
    try:
        return rfc8785.dumps(value)
    except (TypeError, ValueError) as exc:
        raise CounterSignatureFormatError(
            "value cannot be canonicalized using RFC 8785 JCS"
        ) from exc


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    normalized = value.astimezone(UTC).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def resolve_receipt_digest(receipt_or_digest: Any) -> dict[str, str]:
    if hasattr(receipt_or_digest, "to_dict"):
        receipt_or_digest = receipt_or_digest.to_dict()
    if not isinstance(receipt_or_digest, Mapping):
        raise CounterSignatureFormatError(
            "receipt_or_digest must be a Receipt v1 mapping or digest mapping"
        )

    value = dict(receipt_or_digest)
    if {"algorithm", "canonicalization", "value"}.issubset(value):
        return validate_digest(value)

    contract = value.get("contract")
    if (
        not isinstance(contract, Mapping)
        or contract.get("name") != "receipt"
        or contract.get("version") != "v1"
    ):
        raise CounterSignatureFormatError(
            "receipt_or_digest must declare Receipt v1 or provide a complete digest"
        )
    return {
        "algorithm": DIGEST_ALGORITHM,
        "canonicalization": DIGEST_CANONICALIZATION,
        "value": sha256_hex(canonicalize_bytes(value)),
    }


def validate_digest(value: Mapping[str, Any]) -> dict[str, str]:
    algorithm = value.get("algorithm")
    canonicalization = value.get("canonicalization")
    digest_value = value.get("value")
    if (
        algorithm != DIGEST_ALGORITHM
        or canonicalization != DIGEST_CANONICALIZATION
        or not isinstance(digest_value, str)
        or _HEX_256_RE.fullmatch(digest_value) is None
    ):
        raise CounterSignatureFormatError(
            "digest must declare sha-256, RFC8785-JCS, and a lowercase 64-character hex value"
        )
    return {
        "algorithm": algorithm,
        "canonicalization": canonicalization,
        "value": digest_value,
    }


def validate_witness(value: Mapping[str, Any]) -> dict[str, str]:
    witness_type = value.get("type")
    witness_id = value.get("id")
    display_name = value.get("display_name")
    if not isinstance(witness_type, str) or not witness_type:
        raise CounterSignatureFormatError("witness.type must be a non-empty string")
    if not isinstance(witness_id, str) or not witness_id:
        raise CounterSignatureFormatError("witness.id must be a non-empty string")
    if display_name is not None and (not isinstance(display_name, str) or not display_name):
        raise CounterSignatureFormatError(
            "witness.display_name must be a non-empty string when supplied"
        )
    witness = {"type": witness_type, "id": witness_id}
    if display_name is not None:
        witness["display_name"] = display_name
    return witness


def build_signed_statement(
    *,
    receipt_digest: Mapping[str, Any],
    witness: Mapping[str, Any],
    signed_at: str,
    anchor_reference: Mapping[str, Any] | None,
) -> dict[str, Any]:
    statement: dict[str, Any] = {
        "context": COUNTERSIGNATURE_CONTEXT,
        "receipt_digest": validate_digest(receipt_digest),
        "witness": validate_witness(witness),
        "signed_at": signed_at,
    }
    if anchor_reference is not None:
        validate_anchor_reference(anchor_reference)
        statement["anchor_reference"] = dict(anchor_reference)
    return statement


def build_countersignature_artifact(
    *,
    receipt_digest: Mapping[str, Any],
    witness: Mapping[str, Any],
    signed_at: str,
    anchor_reference: Mapping[str, Any] | None,
    key_id: str,
    signature: bytes,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "contract": dict(COUNTERSIGNATURE_CONTRACT),
        "receipt_digest": validate_digest(receipt_digest),
        "witness": validate_witness(witness),
        "signed_at": signed_at,
        "signature": {
            "algorithm": "EdDSA",
            "key_id": key_id,
            "encoding": "base64url",
            "value": base64.urlsafe_b64encode(signature).decode("ascii").rstrip("="),
        },
    }
    if anchor_reference is not None:
        validate_anchor_reference(anchor_reference)
        artifact["anchor_reference"] = dict(anchor_reference)
    return artifact


def validate_anchor_reference(value: Mapping[str, Any]) -> None:
    if not isinstance(value.get("type"), str) or not value["type"]:
        raise CounterSignatureFormatError("anchor_reference.type must be a non-empty string")
    if not isinstance(value.get("id"), str) or not value["id"]:
        raise CounterSignatureFormatError("anchor_reference.id must be a non-empty string")


__all__ = [
    "COUNTERSIGNATURE_CONTEXT",
    "COUNTERSIGNATURE_CONTRACT",
    "COUNTERSIGNATURE_KEY_USE",
    "CounterSignatureFormatError",
    "build_countersignature_artifact",
    "build_signed_statement",
    "canonicalize_bytes",
    "format_timestamp",
    "normalize_utc",
    "resolve_receipt_digest",
    "sha256_hex",
    "validate_digest",
    "validate_witness",
]
