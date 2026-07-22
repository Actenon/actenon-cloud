from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.services.countersigning_format import canonicalize_bytes, format_timestamp, sha256_hex

CHECKPOINT_CONTEXT = "actenon.transparency-checkpoint.v1"
CHECKPOINT_KEY_USE = "transparency_checkpoint"
CHECKPOINT_CONTRACT = {"name": "transparency_checkpoint", "version": "v1"}
INCLUSION_PROOF_CONTRACT = {
    "name": "transparency_inclusion_proof",
    "version": "v1",
}
CONSISTENCY_PROOF_CONTRACT = {
    "name": "transparency_consistency_proof",
    "version": "v1",
}
_HEX_256_RE = re.compile(r"^[0-9a-f]{64}$")


class TransparencyFormatError(ValueError):
    pass


def validate_log_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    identity = dict(value)
    if not isinstance(identity.get("type"), str) or not identity["type"]:
        raise TransparencyFormatError("log identity type must be a non-empty string")
    if not isinstance(identity.get("id"), str) or not identity["id"]:
        raise TransparencyFormatError("log identity id must be a non-empty string")
    return identity


def normalize_receipt_digest(value: Mapping[str, Any] | str) -> dict[str, str]:
    if isinstance(value, str):
        digest_value = value
    else:
        if value.get("algorithm") != "sha-256":
            raise TransparencyFormatError("receipt digest algorithm must be sha-256")
        if value.get("canonicalization") != "RFC8785-JCS":
            raise TransparencyFormatError(
                "receipt digest canonicalization must be RFC8785-JCS"
            )
        digest_value = value.get("value")
    if not isinstance(digest_value, str) or _HEX_256_RE.fullmatch(digest_value) is None:
        raise TransparencyFormatError(
            "receipt digest must be a lowercase 64-character SHA-256 hex value"
        )
    return {
        "algorithm": "sha-256",
        "canonicalization": "RFC8785-JCS",
        "value": digest_value,
    }


def leaf_hash(digest_hex: str) -> bytes:
    normalized = normalize_receipt_digest(digest_hex)
    return hashlib.sha256(b"\x00" + bytes.fromhex(normalized["value"])).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def empty_tree_hash() -> bytes:
    return hashlib.sha256(b"").digest()


def largest_power_of_two_less_than(value: int) -> int:
    if value < 2:
        raise TransparencyFormatError("tree partition requires at least two leaves")
    return 1 << ((value - 1).bit_length() - 1)


def merkle_root(leaf_hashes: Sequence[bytes]) -> bytes:
    if not leaf_hashes:
        return empty_tree_hash()
    if len(leaf_hashes) == 1:
        return leaf_hashes[0]
    split = largest_power_of_two_less_than(len(leaf_hashes))
    return node_hash(
        merkle_root(leaf_hashes[:split]),
        merkle_root(leaf_hashes[split:]),
    )


def inclusion_path(leaf_hashes: Sequence[bytes], leaf_index: int) -> list[str]:
    if not leaf_hashes or leaf_index < 0 or leaf_index >= len(leaf_hashes):
        raise TransparencyFormatError("leaf index is outside the requested tree")
    if len(leaf_hashes) == 1:
        return []
    split = largest_power_of_two_less_than(len(leaf_hashes))
    if leaf_index < split:
        return inclusion_path(leaf_hashes[:split], leaf_index) + [
            merkle_root(leaf_hashes[split:]).hex()
        ]
    return inclusion_path(leaf_hashes[split:], leaf_index - split) + [
        merkle_root(leaf_hashes[:split]).hex()
    ]


def _consistency_path(
    old_size: int,
    leaf_hashes: Sequence[bytes],
    include_old_root: bool,
) -> list[bytes]:
    new_size = len(leaf_hashes)
    if old_size == new_size:
        return [] if include_old_root else [merkle_root(leaf_hashes)]
    split = largest_power_of_two_less_than(new_size)
    if old_size <= split:
        return _consistency_path(
            old_size,
            leaf_hashes[:split],
            include_old_root,
        ) + [merkle_root(leaf_hashes[split:])]
    return _consistency_path(
        old_size - split,
        leaf_hashes[split:],
        False,
    ) + [merkle_root(leaf_hashes[:split])]


def consistency_path(
    leaf_hashes: Sequence[bytes],
    old_size: int,
    new_size: int,
) -> list[str]:
    if old_size < 0 or new_size < old_size or new_size > len(leaf_hashes):
        raise TransparencyFormatError("invalid consistency-proof tree sizes")
    if old_size == 0 or old_size == new_size:
        return []
    return [
        item.hex()
        for item in _consistency_path(old_size, leaf_hashes[:new_size], True)
    ]


def append_chain_hash(
    previous_chain_hash: str | None,
    *,
    leaf_index: int,
    receipt_digest: str,
    computed_leaf_hash: str,
) -> str:
    previous = bytes.fromhex(previous_chain_hash) if previous_chain_hash else b"\x00" * 32
    return hashlib.sha256(
        previous
        + leaf_index.to_bytes(8, "big", signed=False)
        + bytes.fromhex(receipt_digest)
        + bytes.fromhex(computed_leaf_hash)
    ).hexdigest()


def build_checkpoint_statement(
    *,
    log_identity: Mapping[str, Any],
    tree_size: int,
    root_hash: str,
    issued_at: datetime,
) -> dict[str, Any]:
    identity = validate_log_identity(log_identity)
    if tree_size < 0:
        raise TransparencyFormatError("checkpoint tree size must be non-negative")
    if _HEX_256_RE.fullmatch(root_hash) is None:
        raise TransparencyFormatError("checkpoint root must be lowercase SHA-256 hex")
    return {
        "context": CHECKPOINT_CONTEXT,
        "log": identity,
        "tree_size": tree_size,
        "root_hash": {
            "algorithm": "sha-256",
            "encoding": "hex",
            "value": root_hash,
        },
        "issued_at": format_timestamp(issued_at.astimezone(UTC)),
    }


def validate_checkpoint_statement(
    statement: Mapping[str, Any],
    *,
    expected_log_identity: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = dict(statement)
    if set(normalized) != {"context", "log", "tree_size", "root_hash", "issued_at"}:
        raise TransparencyFormatError("checkpoint signing statement has unexpected fields")
    if normalized["context"] != CHECKPOINT_CONTEXT:
        raise TransparencyFormatError("checkpoint signing context is invalid")
    if validate_log_identity(normalized["log"]) != validate_log_identity(
        expected_log_identity
    ):
        raise TransparencyFormatError(
            "checkpoint log identity does not match the managed signing identity"
        )
    tree_size = normalized["tree_size"]
    if isinstance(tree_size, bool) or not isinstance(tree_size, int) or tree_size < 0:
        raise TransparencyFormatError("checkpoint tree size must be non-negative")
    root_hash = normalized["root_hash"]
    if (
        not isinstance(root_hash, Mapping)
        or root_hash.get("algorithm") != "sha-256"
        or root_hash.get("encoding") != "hex"
        or not isinstance(root_hash.get("value"), str)
        or _HEX_256_RE.fullmatch(root_hash["value"]) is None
    ):
        raise TransparencyFormatError("checkpoint root hash is invalid")
    issued_at = normalized["issued_at"]
    if not isinstance(issued_at, str) or not issued_at.endswith("Z"):
        raise TransparencyFormatError("checkpoint issued_at must be an RFC3339 UTC timestamp")
    try:
        datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransparencyFormatError(
            "checkpoint issued_at must be an RFC3339 UTC timestamp"
        ) from exc
    return normalized


def build_checkpoint_artifact(
    *,
    statement: Mapping[str, Any],
    key_id: str,
    signature: bytes,
) -> dict[str, Any]:
    return {
        "contract": dict(CHECKPOINT_CONTRACT),
        "log": dict(statement["log"]),
        "tree_size": statement["tree_size"],
        "root_hash": dict(statement["root_hash"]),
        "issued_at": statement["issued_at"],
        "signature": {
            "algorithm": "EdDSA",
            "key_id": key_id,
            "encoding": "base64url",
            "value": base64.urlsafe_b64encode(signature)
            .decode("ascii")
            .rstrip("="),
        },
    }


def build_inclusion_proof(
    *,
    log_id: str,
    tree_size: int,
    leaf_index: int,
    receipt_digest: str,
    audit_path: Sequence[str],
) -> dict[str, Any]:
    return {
        "contract": dict(INCLUSION_PROOF_CONTRACT),
        "log_id": log_id,
        "hash_algorithm": "sha-256",
        "tree_size": tree_size,
        "leaf_index": leaf_index,
        "leaf_digest": normalize_receipt_digest(receipt_digest),
        "audit_path": list(audit_path),
    }


def build_consistency_proof(
    *,
    log_id: str,
    old_tree_size: int,
    new_tree_size: int,
    path: Sequence[str],
) -> dict[str, Any]:
    return {
        "contract": dict(CONSISTENCY_PROOF_CONTRACT),
        "log_id": log_id,
        "hash_algorithm": "sha-256",
        "old_tree_size": old_tree_size,
        "new_tree_size": new_tree_size,
        "consistency_path": list(path),
    }


def artifact_digest(artifact: Mapping[str, Any]) -> str:
    return sha256_hex(canonicalize_bytes(dict(artifact)))


__all__ = [
    "CHECKPOINT_CONTEXT",
    "CHECKPOINT_KEY_USE",
    "TransparencyFormatError",
    "append_chain_hash",
    "artifact_digest",
    "build_checkpoint_artifact",
    "build_checkpoint_statement",
    "build_consistency_proof",
    "build_inclusion_proof",
    "canonicalize_bytes",
    "consistency_path",
    "inclusion_path",
    "leaf_hash",
    "merkle_root",
    "normalize_receipt_digest",
    "validate_checkpoint_statement",
    "validate_log_identity",
]
