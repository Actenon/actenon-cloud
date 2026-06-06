from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models import EvidenceStorageMode
from app.services.evidence_backends import (
    EvidenceBackendNotReadyError,
    EvidenceContentUnsupportedError,
    FilesystemEvidenceBackend,
    ObjectStoreEvidenceBackend,
)


def test_filesystem_evidence_backend_stores_and_reads_uploaded_content(
    tmp_path: Path,
) -> None:
    backend = FilesystemEvidenceBackend(tmp_path / "evidence")

    stored_artifact = backend.store_upload(
        tenant_id="tenant-123",
        action_intent_record_id="intent-123",
        evidence_object_id="evidence-123",
        filename="wire-proof.pdf",
        payload=b"evidence-bytes",
    )

    assert stored_artifact.storage_mode == EvidenceStorageMode.filesystem
    assert stored_artifact.content_digest
    assert stored_artifact.size_bytes == len(b"evidence-bytes")

    evidence_object = SimpleNamespace(
        storage_ref=stored_artifact.storage_ref,
        evidence_object_id="evidence-123",
    )
    content_path = backend.open_content(evidence_object)

    assert content_path.read_bytes() == b"evidence-bytes"


def test_object_store_evidence_backend_fails_clearly_until_implemented() -> None:
    backend = ObjectStoreEvidenceBackend(
        bucket="pilot-evidence",
        prefix="invoice-payment/evidence",
        endpoint="https://object-storage.example",
    )

    with pytest.raises(EvidenceBackendNotReadyError, match="not implemented"):
        backend.store_upload(
            tenant_id="tenant-123",
            action_intent_record_id="intent-123",
            evidence_object_id="evidence-123",
            filename="wire-proof.pdf",
            payload=b"evidence-bytes",
        )

    evidence_object = SimpleNamespace(
        storage_ref="invoice-payment/evidence/evidence-123",
        evidence_object_id="evidence-123",
    )
    with pytest.raises(EvidenceContentUnsupportedError, match="not implemented"):
        backend.open_content(evidence_object)
