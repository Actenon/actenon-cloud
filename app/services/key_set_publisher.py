from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.services.countersigning_format import canonicalize_bytes, sha256_hex


class KeySetPublicationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PublishedKeySet:
    version: str
    digest: str
    publication_reference: str


class KeySetPublisher(Protocol):
    def publish(
        self,
        *,
        document: Mapping[str, Any],
        version: str,
    ) -> PublishedKeySet: ...


class AtomicFileKeySetPublisher:
    """Atomically publishes public-only key-set JSON for a separate HTTPS origin."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def publish(
        self,
        *,
        document: Mapping[str, Any],
        version: str,
    ) -> PublishedKeySet:
        if not version or "/" in version or "\\" in version:
            raise KeySetPublicationError("key-set version must be a path-safe identifier")
        payload = canonicalize_bytes(dict(document)) + b"\n"
        digest = sha256_hex(payload.rstrip(b"\n"))

        version_dir = self._root / "versions"
        current_path = self._root / ".well-known" / "actenon" / "keys.json"
        version_path = version_dir / f"{version}.json"
        version_dir.mkdir(parents=True, exist_ok=True)
        current_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._atomic_write(version_path, payload)
            self._atomic_write(current_path, payload)
        except OSError as exc:
            raise KeySetPublicationError("failed to publish public counter-signing keys") from exc

        return PublishedKeySet(
            version=version,
            digest=digest,
            publication_reference=str(current_path),
        )

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        temporary_path = path.with_name(f".{path.name}.tmp")
        with temporary_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)


__all__ = [
    "AtomicFileKeySetPublisher",
    "KeySetPublicationError",
    "KeySetPublisher",
    "PublishedKeySet",
]
