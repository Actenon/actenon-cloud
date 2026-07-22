from __future__ import annotations

from actenon.verifier import verify_consistency, verify_inclusion

from app.services.transparency_format import (
    build_consistency_proof,
    build_inclusion_proof,
    consistency_path,
    inclusion_path,
    leaf_hash,
    merkle_root,
)


def digest(number: int) -> str:
    return f"{number:064x}"


def digest_spec(number: int) -> dict[str, str]:
    return {
        "algorithm": "sha-256",
        "canonicalization": "RFC8785-JCS",
        "value": digest(number),
    }


def checkpoint(tree_size: int, root_hash: str) -> dict[str, object]:
    return {
        "contract": {
            "name": "transparency_checkpoint",
            "version": "v1",
        },
        "log": {
            "type": "service",
            "id": "exhaustive-merkle-test",
        },
        "tree_size": tree_size,
        "root_hash": {
            "algorithm": "sha-256",
            "encoding": "hex",
            "value": root_hash,
        },
        "issued_at": "2026-06-06T12:00:00Z",
        "signature": {
            "algorithm": "EdDSA",
            "key_id": "not-verified-by-proof-routines",
            "encoding": "base64url",
            "value": "AA",
        },
    }


def test_generated_proofs_verify_for_non_power_of_two_trees() -> None:
    hashes = [leaf_hash(digest(number)) for number in range(1, 33)]

    for tree_size in range(1, 33):
        current_hashes = hashes[:tree_size]
        current_checkpoint = checkpoint(
            tree_size,
            merkle_root(current_hashes).hex(),
        )
        for leaf_index in range(tree_size):
            proof = build_inclusion_proof(
                log_id="exhaustive-merkle-test",
                tree_size=tree_size,
                leaf_index=leaf_index,
                receipt_digest=digest(leaf_index + 1),
                audit_path=inclusion_path(current_hashes, leaf_index),
            )
            assert verify_inclusion(
                digest_spec(leaf_index + 1),
                proof,
                current_checkpoint,
            ).leaf_index == leaf_index

        for old_size in range(1, tree_size + 1):
            old_checkpoint = checkpoint(
                old_size,
                merkle_root(hashes[:old_size]).hex(),
            )
            proof = build_consistency_proof(
                log_id="exhaustive-merkle-test",
                old_tree_size=old_size,
                new_tree_size=tree_size,
                path=consistency_path(hashes, old_size, tree_size),
            )
            verified = verify_consistency(
                old_checkpoint,
                current_checkpoint,
                proof,
            )
            assert (verified.old_tree_size, verified.new_tree_size) == (
                old_size,
                tree_size,
            )
