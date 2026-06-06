from __future__ import annotations

import base64
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.services.countersigning_format import (
    canonicalize_bytes,
    format_timestamp,
)

ISSUER_STATUS_CONTEXT = "actenon.issuer-status.v1"
ISSUER_STATUS_CONTRACT = {"name": "issuer_status", "version": "v1"}
ISSUER_STATUS_KEY_USE = "issuer_status"
ISSUER_STANDINGS = frozenset({"good_standing", "suspended", "revoked"})


class IssuerStatusFormatError(ValueError):
    pass


def validate_party(value: Mapping[str, Any], *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise IssuerStatusFormatError(f"{field_name} must be a JSON object")
    party_type = value.get("type")
    party_id = value.get("id")
    display_name = value.get("display_name")
    if not isinstance(party_type, str) or not party_type:
        raise IssuerStatusFormatError(f"{field_name}.type must be a non-empty string")
    if not isinstance(party_id, str) or not party_id:
        raise IssuerStatusFormatError(f"{field_name}.id must be a non-empty string")
    if display_name is not None and (
        not isinstance(display_name, str) or not display_name
    ):
        raise IssuerStatusFormatError(
            f"{field_name}.display_name must be a non-empty string when supplied"
        )
    party: dict[str, Any] = {"type": party_type, "id": party_id}
    if display_name is not None:
        party["display_name"] = display_name
    return party


def build_issuer_status_statement(
    *,
    issuer: Mapping[str, Any],
    authority: Mapping[str, Any],
    status: str,
    issued_at: datetime,
    expires_at: datetime,
    status_reference: str | None,
) -> dict[str, Any]:
    if status not in ISSUER_STANDINGS:
        raise IssuerStatusFormatError("issuer status is invalid")
    if expires_at <= issued_at:
        raise IssuerStatusFormatError("issuer status expiry must be after issuance")
    statement: dict[str, Any] = {
        "context": ISSUER_STATUS_CONTEXT,
        "issuer": validate_party(issuer, field_name="issuer"),
        "authority": validate_party(authority, field_name="authority"),
        "status": status,
        "issued_at": format_timestamp(issued_at),
        "expires_at": format_timestamp(expires_at),
    }
    if status_reference is not None:
        if not status_reference:
            raise IssuerStatusFormatError(
                "status_reference must be non-empty when supplied"
            )
        statement["status_reference"] = status_reference
    return statement


def validate_issuer_status_statement(
    statement: Mapping[str, Any],
    *,
    expected_authority: Mapping[str, Any],
) -> dict[str, Any]:
    allowed_fields = {
        "context",
        "issuer",
        "authority",
        "status",
        "issued_at",
        "expires_at",
        "status_reference",
    }
    if not set(statement).issubset(allowed_fields) or not {
        "context",
        "issuer",
        "authority",
        "status",
        "issued_at",
        "expires_at",
    }.issubset(statement):
        raise IssuerStatusFormatError(
            "issuer-status signing statement has unexpected or missing fields"
        )
    if statement["context"] != ISSUER_STATUS_CONTEXT:
        raise IssuerStatusFormatError("issuer-status signing context is invalid")
    issuer = validate_party(statement["issuer"], field_name="issuer")
    authority = validate_party(statement["authority"], field_name="authority")
    if authority != validate_party(expected_authority, field_name="expected_authority"):
        raise IssuerStatusFormatError(
            "issuer-status authority does not match the managed signing identity"
        )
    status = statement["status"]
    if status not in ISSUER_STANDINGS:
        raise IssuerStatusFormatError("issuer status is invalid")
    try:
        issued_at = datetime.fromisoformat(
            str(statement["issued_at"]).replace("Z", "+00:00")
        )
        expires_at = datetime.fromisoformat(
            str(statement["expires_at"]).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise IssuerStatusFormatError(
            "issuer-status timestamps must be RFC3339"
        ) from exc
    if issued_at.tzinfo is None or expires_at.tzinfo is None:
        raise IssuerStatusFormatError(
            "issuer-status timestamps must include an RFC3339 timezone"
        )
    if expires_at <= issued_at:
        raise IssuerStatusFormatError("issuer status expiry must be after issuance")
    normalized = {
        "context": ISSUER_STATUS_CONTEXT,
        "issuer": issuer,
        "authority": authority,
        "status": status,
        "issued_at": statement["issued_at"],
        "expires_at": statement["expires_at"],
    }
    status_reference = statement.get("status_reference")
    if status_reference is not None:
        if not isinstance(status_reference, str) or not status_reference:
            raise IssuerStatusFormatError(
                "status_reference must be non-empty when supplied"
            )
        normalized["status_reference"] = status_reference
    return normalized


def build_issuer_status_artifact(
    *,
    statement: Mapping[str, Any],
    key_id: str,
    signature: bytes,
) -> dict[str, Any]:
    if not key_id:
        raise IssuerStatusFormatError("issuer-status key_id must be non-empty")
    if len(signature) != 64:
        raise IssuerStatusFormatError(
            "issuer-status signature must be 64-byte Ed25519"
        )
    artifact = {
        key: value
        for key, value in statement.items()
        if key != "context"
    }
    return {
        "contract": dict(ISSUER_STATUS_CONTRACT),
        **artifact,
        "signature": {
            "algorithm": "EdDSA",
            "key_id": key_id,
            "encoding": "base64url",
            "value": base64.urlsafe_b64encode(signature)
            .decode("ascii")
            .rstrip("="),
        },
    }


__all__ = [
    "ISSUER_STATUS_CONTEXT",
    "ISSUER_STATUS_CONTRACT",
    "ISSUER_STATUS_KEY_USE",
    "ISSUER_STANDINGS",
    "IssuerStatusFormatError",
    "build_issuer_status_artifact",
    "build_issuer_status_statement",
    "canonicalize_bytes",
    "validate_issuer_status_statement",
    "validate_party",
]
