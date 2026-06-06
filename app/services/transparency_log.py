from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.metrics import get_metrics_registry
from app.models import (
    TransparencyCheckpointRecord,
    TransparencyCheckpointStatus,
    TransparencyIntegrityEvent,
    TransparencyLogLeaf,
    TransparencyLogState,
)
from app.services.countersigning import (
    CounterSigningService,
    ManagedCheckpointSignature,
    PrincipalContext,
)
from app.services.countersigning_format import normalize_utc, sha256_hex
from app.services.transparency_format import (
    append_chain_hash,
    artifact_digest,
    build_checkpoint_artifact,
    build_checkpoint_statement,
    build_consistency_proof,
    build_inclusion_proof,
    canonicalize_bytes,
    consistency_path,
    inclusion_path,
    leaf_hash,
    merkle_root,
    normalize_receipt_digest,
    validate_log_identity,
)


class TransparencyLogError(RuntimeError):
    pass


class TransparencyLogConfigurationError(TransparencyLogError):
    pass


class TransparencyLogNotFoundError(TransparencyLogError):
    pass


class TransparencyLogIntegrityError(TransparencyLogError):
    pass


class CheckpointSigner(Protocol):
    def sign(
        self,
        statement: Mapping[str, Any],
        *,
        idempotency_token: str,
    ) -> ManagedCheckpointSignature: ...


class CounterSigningCheckpointSigner:
    """Uses the P10 managed custody service without exposing private key material."""

    def __init__(
        self,
        service: CounterSigningService,
        *,
        authority: PrincipalContext,
    ) -> None:
        self._service = service
        self._authority = authority

    def sign(
        self,
        statement: Mapping[str, Any],
        *,
        idempotency_token: str,
    ) -> ManagedCheckpointSignature:
        return self._service.sign_transparency_checkpoint(
            statement,
            authority=self._authority,
            idempotency_token=idempotency_token,
        )


@dataclass(frozen=True, slots=True)
class TransparencyActor:
    principal_type: str
    principal_id: str


@dataclass(frozen=True, slots=True)
class LeafAppendResult:
    leaf_index: int
    receipt_digest: dict[str, str]
    idempotent_replay: bool


@dataclass(frozen=True, slots=True)
class CheckpointPublicationResult:
    checkpoint: dict[str, Any]
    checkpoint_digest: str
    idempotent_replay: bool


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    log_id: str
    ok: bool
    leaf_count: int
    checkpoint_count: int
    latest_checkpoint_size: int | None
    error_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_id": self.log_id,
            "ok": self.ok,
            "leaf_count": self.leaf_count,
            "checkpoint_count": self.checkpoint_count,
            "latest_checkpoint_size": self.latest_checkpoint_size,
            "error_codes": list(self.error_codes),
        }


class TransparencyLogService:
    def __init__(
        self,
        session: Session,
        *,
        log_identity: Mapping[str, Any],
        checkpoint_signer: CheckpointSigner | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.log_identity = validate_log_identity(log_identity)
        self.log_id = self.log_identity["id"]
        self.checkpoint_signer = checkpoint_signer
        self.clock = clock or (lambda: datetime.now(UTC))

    def append_receipt_digest(
        self,
        receipt_digest: Mapping[str, Any] | str,
    ) -> LeafAppendResult:
        digest = normalize_receipt_digest(receipt_digest)
        state = self._locked_state(create=True)
        existing = self.session.scalar(
            select(TransparencyLogLeaf).where(
                TransparencyLogLeaf.log_id == self.log_id,
                TransparencyLogLeaf.receipt_digest == digest["value"],
            )
        )
        if existing is not None:
            return LeafAppendResult(
                leaf_index=existing.leaf_index,
                receipt_digest=digest,
                idempotent_replay=True,
            )

        index = state.next_leaf_index
        computed_leaf_hash = leaf_hash(digest["value"]).hex()
        chain_hash = append_chain_hash(
            state.append_chain_head,
            leaf_index=index,
            receipt_digest=digest["value"],
            computed_leaf_hash=computed_leaf_hash,
        )
        leaf = TransparencyLogLeaf(
            leaf_id=uuid4().hex,
            log_id=self.log_id,
            leaf_index=index,
            receipt_digest=digest["value"],
            leaf_hash=computed_leaf_hash,
            append_chain_hash=chain_hash,
            ingested_at=self._now(),
        )
        state.next_leaf_index = index + 1
        state.append_chain_head = chain_hash
        self.session.add_all([leaf, state])
        self.session.commit()

        get_metrics_registry().counter(
            "action_control_plane_transparency_log_leaves_total",
            "Receipt digests appended to transparency logs.",
            label_names=("log_id",),
        ).inc(log_id=self.log_id)
        return LeafAppendResult(
            leaf_index=index,
            receipt_digest=digest,
            idempotent_replay=False,
        )

    def publish_checkpoint(
        self,
        *,
        actor: TransparencyActor,
    ) -> CheckpointPublicationResult:
        if self.checkpoint_signer is None:
            raise TransparencyLogConfigurationError(
                "transparency checkpoint signer is not configured"
            )
        state = self._locked_state(create=False)
        if state is None or state.next_leaf_index == 0:
            raise TransparencyLogNotFoundError(
                "cannot publish a checkpoint for an empty transparency log"
            )

        integrity = self.audit_integrity(record_failure=True)
        if not integrity.ok:
            raise TransparencyLogIntegrityError(
                "transparency log failed its pre-publication integrity check"
            )

        leaves = self._leaves()
        tree_size = len(leaves)
        root_hash = merkle_root([bytes.fromhex(item.leaf_hash) for item in leaves]).hex()
        existing = self.session.scalar(
            select(TransparencyCheckpointRecord).where(
                TransparencyCheckpointRecord.log_id == self.log_id,
                TransparencyCheckpointRecord.tree_size == tree_size,
            )
        )
        if (
            existing is not None
            and existing.status == TransparencyCheckpointStatus.completed
            and existing.root_hash == root_hash
            and existing.checkpoint_artifact is not None
            and existing.checkpoint_digest is not None
        ):
            return CheckpointPublicationResult(
                checkpoint=dict(existing.checkpoint_artifact),
                checkpoint_digest=existing.checkpoint_digest,
                idempotent_replay=True,
            )
        if existing is None:
            existing = TransparencyCheckpointRecord(
                checkpoint_id=uuid4().hex,
                log_id=self.log_id,
                tree_size=tree_size,
                root_hash=root_hash,
                status=TransparencyCheckpointStatus.requested,
                prior_checkpoint_digest=state.latest_checkpoint_digest,
                actor_principal_type=actor.principal_type,
                actor_principal_id=actor.principal_id,
            )
        else:
            existing.root_hash = root_hash
            existing.status = TransparencyCheckpointStatus.requested
            existing.prior_checkpoint_digest = state.latest_checkpoint_digest
            existing.actor_principal_type = actor.principal_type
            existing.actor_principal_id = actor.principal_id
            existing.error_code = None
            existing.error_detail = None
        self.session.add(existing)
        self.session.flush()

        issued_at = self._now()
        statement = build_checkpoint_statement(
            log_identity=self.log_identity,
            tree_size=tree_size,
            root_hash=root_hash,
            issued_at=issued_at,
        )
        existing.signing_input_digest = sha256_hex(canonicalize_bytes(statement))
        try:
            signed = self.checkpoint_signer.sign(
                statement,
                idempotency_token=existing.checkpoint_id,
            )
            artifact = build_checkpoint_artifact(
                statement=statement,
                key_id=signed.key_id,
                signature=signed.signature,
            )
        except Exception as exc:
            existing.status = TransparencyCheckpointStatus.failed
            existing.error_code = exc.__class__.__name__
            existing.error_detail = "managed checkpoint signing failed closed"
            existing.completed_at = self._now()
            self.session.add(existing)
            self.session.commit()
            raise

        checkpoint_digest = artifact_digest(artifact)
        existing.key_id = signed.key_id
        existing.provider_operation_ref = signed.provider_operation_ref
        existing.checkpoint_artifact = artifact
        existing.checkpoint_digest = checkpoint_digest
        existing.status = TransparencyCheckpointStatus.completed
        existing.issued_at = issued_at
        existing.completed_at = self._now()
        state.latest_checkpoint_size = tree_size
        state.latest_checkpoint_digest = checkpoint_digest
        self.session.add_all([existing, state])
        self.session.commit()

        metrics = get_metrics_registry()
        metrics.counter(
            "action_control_plane_transparency_checkpoints_total",
            "Transparency checkpoints published by log and key identifier.",
            label_names=("log_id", "key_id"),
        ).inc(log_id=self.log_id, key_id=signed.key_id)
        metrics.gauge(
            "action_control_plane_transparency_tree_size",
            "Latest published transparency-log tree size.",
            label_names=("log_id",),
        ).set(tree_size, log_id=self.log_id)
        return CheckpointPublicationResult(
            checkpoint=artifact,
            checkpoint_digest=checkpoint_digest,
            idempotent_replay=False,
        )

    def latest_checkpoint(self) -> dict[str, Any]:
        record = self.session.scalar(
            select(TransparencyCheckpointRecord)
            .where(
                TransparencyCheckpointRecord.log_id == self.log_id,
                TransparencyCheckpointRecord.status
                == TransparencyCheckpointStatus.completed,
            )
            .order_by(TransparencyCheckpointRecord.tree_size.desc())
            .limit(1)
        )
        return self._checkpoint_artifact(record)

    def list_checkpoints(self) -> list[dict[str, Any]]:
        records = list(
            self.session.scalars(
                select(TransparencyCheckpointRecord)
                .where(
                    TransparencyCheckpointRecord.log_id == self.log_id,
                    TransparencyCheckpointRecord.status
                    == TransparencyCheckpointStatus.completed,
                )
                .order_by(TransparencyCheckpointRecord.tree_size.asc())
            )
        )
        return [self._checkpoint_artifact(record) for record in records]

    def inclusion_proof(
        self,
        receipt_digest: Mapping[str, Any] | str,
        *,
        tree_size: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        digest = normalize_receipt_digest(receipt_digest)
        checkpoint = self._checkpoint_record(tree_size)
        leaves = self._leaves(limit=checkpoint.tree_size)
        matching = next(
            (item for item in leaves if item.receipt_digest == digest["value"]),
            None,
        )
        if matching is None:
            raise TransparencyLogNotFoundError(
                "receipt digest is not included in the requested checkpoint"
            )
        proof = build_inclusion_proof(
            log_id=self.log_id,
            tree_size=checkpoint.tree_size,
            leaf_index=matching.leaf_index,
            receipt_digest=matching.receipt_digest,
            audit_path=inclusion_path(
                [bytes.fromhex(item.leaf_hash) for item in leaves],
                matching.leaf_index,
            ),
        )
        return proof, self._checkpoint_artifact(checkpoint)

    def consistency_proof(
        self,
        *,
        old_tree_size: int,
        new_tree_size: int,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        old_checkpoint = self._checkpoint_record(old_tree_size)
        new_checkpoint = self._checkpoint_record(new_tree_size)
        leaves = self._leaves(limit=new_tree_size)
        path = consistency_path(
            [bytes.fromhex(item.leaf_hash) for item in leaves],
            old_tree_size,
            new_tree_size,
        )
        proof = build_consistency_proof(
            log_id=self.log_id,
            old_tree_size=old_tree_size,
            new_tree_size=new_tree_size,
            path=path,
        )
        return (
            proof,
            self._checkpoint_artifact(old_checkpoint),
            self._checkpoint_artifact(new_checkpoint),
        )

    def monitor_update(
        self,
        *,
        previous_tree_size: int,
    ) -> dict[str, Any]:
        latest = self._checkpoint_record(None)
        proof, previous, current = self.consistency_proof(
            old_tree_size=previous_tree_size,
            new_tree_size=latest.tree_size,
        )
        return {
            "previous_checkpoint": previous,
            "current_checkpoint": current,
            "consistency_proof": proof,
        }

    def audit_integrity(self, *, record_failure: bool = True) -> IntegrityReport:
        state = self._locked_state(create=False)
        leaves = self._leaves()
        checkpoints = list(
            self.session.scalars(
                select(TransparencyCheckpointRecord)
                .where(
                    TransparencyCheckpointRecord.log_id == self.log_id,
                    TransparencyCheckpointRecord.status
                    == TransparencyCheckpointStatus.completed,
                )
                .order_by(TransparencyCheckpointRecord.tree_size.asc())
            )
        )
        errors: list[str] = []
        previous_chain: str | None = None
        for expected_index, leaf in enumerate(leaves):
            expected_leaf_hash = leaf_hash(leaf.receipt_digest).hex()
            if leaf.leaf_index != expected_index:
                errors.append("LEAF_INDEX_GAP")
            if leaf.leaf_hash != expected_leaf_hash:
                errors.append("LEAF_HASH_MISMATCH")
            expected_chain = append_chain_hash(
                previous_chain,
                leaf_index=leaf.leaf_index,
                receipt_digest=leaf.receipt_digest,
                computed_leaf_hash=expected_leaf_hash,
            )
            if leaf.append_chain_hash != expected_chain:
                errors.append("APPEND_CHAIN_MISMATCH")
            previous_chain = expected_chain

        if state is None:
            if leaves or checkpoints:
                errors.append("LOG_STATE_MISSING")
        else:
            if state.next_leaf_index != len(leaves):
                errors.append("TREE_SIZE_STATE_MISMATCH")
            if state.append_chain_head != previous_chain:
                errors.append("APPEND_CHAIN_HEAD_MISMATCH")

        prior_checkpoint_digest: str | None = None
        prior_tree_size = -1
        for checkpoint in checkpoints:
            if checkpoint.tree_size <= prior_tree_size:
                errors.append("CHECKPOINT_NON_MONOTONIC")
            if checkpoint.tree_size > len(leaves):
                errors.append("CHECKPOINT_AHEAD_OF_LOG")
                continue
            expected_root = merkle_root(
                [bytes.fromhex(item.leaf_hash) for item in leaves[: checkpoint.tree_size]]
            ).hex()
            if checkpoint.root_hash != expected_root:
                errors.append("CHECKPOINT_ROOT_MISMATCH")
            if checkpoint.prior_checkpoint_digest != prior_checkpoint_digest:
                errors.append("CHECKPOINT_CHAIN_MISMATCH")
            if checkpoint.checkpoint_artifact is None:
                errors.append("CHECKPOINT_ARTIFACT_MISSING")
            elif checkpoint.checkpoint_digest != artifact_digest(
                checkpoint.checkpoint_artifact
            ):
                errors.append("CHECKPOINT_DIGEST_MISMATCH")
            prior_checkpoint_digest = checkpoint.checkpoint_digest
            prior_tree_size = checkpoint.tree_size

        if state is not None:
            expected_latest_size = checkpoints[-1].tree_size if checkpoints else None
            expected_latest_digest = (
                checkpoints[-1].checkpoint_digest if checkpoints else None
            )
            if state.latest_checkpoint_size != expected_latest_size:
                errors.append("LATEST_CHECKPOINT_SIZE_MISMATCH")
            if state.latest_checkpoint_digest != expected_latest_digest:
                errors.append("LATEST_CHECKPOINT_DIGEST_MISMATCH")

        unique_errors = tuple(dict.fromkeys(errors))
        report = IntegrityReport(
            log_id=self.log_id,
            ok=not unique_errors,
            leaf_count=len(leaves),
            checkpoint_count=len(checkpoints),
            latest_checkpoint_size=(
                checkpoints[-1].tree_size if checkpoints else None
            ),
            error_codes=unique_errors,
        )
        if unique_errors and record_failure:
            self.session.add(
                TransparencyIntegrityEvent(
                    event_id=uuid4().hex,
                    log_id=self.log_id,
                    event_type="TRANSPARENCY_LOG_INTEGRITY_FAILURE",
                    severity="critical",
                    details={
                        "error_codes": list(unique_errors),
                        "leaf_count": len(leaves),
                        "checkpoint_count": len(checkpoints),
                    },
                    detected_at=self._now(),
                )
            )
            self.session.commit()
            get_metrics_registry().counter(
                "action_control_plane_transparency_integrity_failures_total",
                "Detected transparency-log integrity failures.",
                label_names=("log_id",),
            ).inc(log_id=self.log_id)
        return report

    def _locked_state(
        self,
        *,
        create: bool,
    ) -> TransparencyLogState | None:
        state = self.session.scalar(
            select(TransparencyLogState)
            .where(TransparencyLogState.log_id == self.log_id)
            .with_for_update()
        )
        if state is None and create:
            state = TransparencyLogState(
                log_id=self.log_id,
                log_identity=dict(self.log_identity),
                next_leaf_index=0,
            )
            self.session.add(state)
            self.session.flush()
        if state is not None and dict(state.log_identity) != self.log_identity:
            raise TransparencyLogIntegrityError(
                "stored transparency-log identity does not match configured identity"
            )
        return state

    def _leaves(self, *, limit: int | None = None) -> list[TransparencyLogLeaf]:
        query = (
            select(TransparencyLogLeaf)
            .where(TransparencyLogLeaf.log_id == self.log_id)
            .order_by(TransparencyLogLeaf.leaf_index.asc())
        )
        if limit is not None:
            query = query.where(TransparencyLogLeaf.leaf_index < limit)
        return list(self.session.scalars(query))

    def _checkpoint_record(
        self,
        tree_size: int | None,
    ) -> TransparencyCheckpointRecord:
        query = select(TransparencyCheckpointRecord).where(
            TransparencyCheckpointRecord.log_id == self.log_id,
            TransparencyCheckpointRecord.status == TransparencyCheckpointStatus.completed,
        )
        if tree_size is None:
            query = query.order_by(TransparencyCheckpointRecord.tree_size.desc()).limit(1)
        else:
            query = query.where(TransparencyCheckpointRecord.tree_size == tree_size)
        record = self.session.scalar(query)
        if record is None:
            target = "latest" if tree_size is None else str(tree_size)
            raise TransparencyLogNotFoundError(
                f"transparency checkpoint '{target}' was not found"
            )
        return record

    @staticmethod
    def _checkpoint_artifact(
        record: TransparencyCheckpointRecord | None,
    ) -> dict[str, Any]:
        if record is None or record.checkpoint_artifact is None:
            raise TransparencyLogNotFoundError("transparency checkpoint was not found")
        return dict(record.checkpoint_artifact)

    def _now(self) -> datetime:
        return normalize_utc(self.clock())


__all__ = [
    "CheckpointPublicationResult",
    "CheckpointSigner",
    "CounterSigningCheckpointSigner",
    "IntegrityReport",
    "LeafAppendResult",
    "TransparencyActor",
    "TransparencyLogConfigurationError",
    "TransparencyLogError",
    "TransparencyLogIntegrityError",
    "TransparencyLogNotFoundError",
    "TransparencyLogService",
]
