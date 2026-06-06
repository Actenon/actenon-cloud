from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from app.models import EvidenceObject, EvidenceStorageMode


class EvidenceBackendError(RuntimeError):
    pass


class EvidenceBackendNotReadyError(EvidenceBackendError):
    pass


class EvidenceContentUnsupportedError(EvidenceBackendError):
    pass


@dataclass(frozen=True, slots=True)
class StoredEvidenceArtifact:
    storage_mode: EvidenceStorageMode
    storage_ref: str
    content_digest: str
    size_bytes: int


def _resolve_root(root_value: str | Path) -> Path:
    root = Path(root_value).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


class EvidenceBackend(ABC):
    storage_mode: EvidenceStorageMode

    @abstractmethod
    def store_upload(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        evidence_object_id: str,
        filename: str,
        payload: bytes,
    ) -> StoredEvidenceArtifact:
        raise NotImplementedError

    @abstractmethod
    def open_content(self, evidence_object: EvidenceObject) -> Path:
        raise NotImplementedError


class FilesystemEvidenceBackend(EvidenceBackend):
    storage_mode = EvidenceStorageMode.filesystem

    def __init__(self, root: str | Path) -> None:
        self.root = _resolve_root(root)

    def store_upload(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        evidence_object_id: str,
        filename: str,
        payload: bytes,
    ) -> StoredEvidenceArtifact:
        suffix = Path(filename or "upload.bin").suffix[:16]
        directory = self.root / tenant_id / action_intent_record_id
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{evidence_object_id}{suffix}"
        target.write_bytes(payload)
        return StoredEvidenceArtifact(
            storage_mode=self.storage_mode,
            storage_ref=str(target.relative_to(self.root)),
            content_digest=sha256(payload).hexdigest(),
            size_bytes=len(payload),
        )

    def open_content(self, evidence_object: EvidenceObject) -> Path:
        candidate = (self.root / evidence_object.storage_ref).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise EvidenceContentUnsupportedError("evidence storage reference is invalid")
        if not candidate.is_file():
            raise FileNotFoundError(
                f"stored evidence file for '{evidence_object.evidence_object_id}' was not found"
            )
        return candidate


class ObjectStoreEvidenceBackend(EvidenceBackend):
    storage_mode = EvidenceStorageMode.object_store

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "evidence",
        endpoint: str | None = None,
    ) -> None:
        normalized_bucket = bucket.strip()
        if not normalized_bucket:
            raise ValueError("object-store evidence backend requires a bucket or namespace")
        normalized_prefix = prefix.strip().strip("/")
        if not normalized_prefix:
            raise ValueError("object-store evidence backend requires a non-empty prefix")
        self.bucket = normalized_bucket
        self.prefix = normalized_prefix
        self.endpoint = endpoint.strip() if endpoint else None

    def store_upload(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        evidence_object_id: str,
        filename: str,
        payload: bytes,
    ) -> StoredEvidenceArtifact:
        raise EvidenceBackendNotReadyError(
            "object-store evidence upload backend is configured "
            "but not implemented in this repo build"
        )

    def open_content(self, evidence_object: EvidenceObject) -> Path:
        raise EvidenceContentUnsupportedError(
            "object-store evidence content retrieval is not implemented in this repo build"
        )
