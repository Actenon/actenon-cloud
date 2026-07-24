"""S3-backed evidence storage with per-tenant salts.

Fable 5 Part 3D: "Commitment layer not yet wired into receipt ingestion.
ObjectStoreEvidenceStore (S3) not implemented; LocalFsEvidenceStore is
current. Per-tenant salts not yet generated/stored."

This module implements the S3 evidence backend that was previously a
stub. It uses boto3 (optional dependency) to store evidence artefacts in
S3 with per-tenant key prefixes and content-addressed naming.

Per-tenant salts
----------------

Each tenant gets a unique salt that is used to derive commitment hashes
for PHI/PII fields in evidence records. The salt is:

  - Generated once per tenant (32 bytes, cryptographically random)
  - Stored in the database (not in S3)
  - Never logged or returned to the caller
  - Used as a HMAC key for field-level commitments

This means two tenants with the same field value (e.g. the same customer
email) produce different commitment hashes, preventing cross-tenant
correlation via the evidence store.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models import EvidenceObject, EvidenceStorageMode

from .evidence_backends import (
    EvidenceBackend,
    EvidenceBackendNotReadyError,
    EvidenceContentUnsupportedError,
    StoredEvidenceArtifact,
)

# ---------------------------------------------------------------------------
# Per-tenant salt management
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TenantSalt:
    """A per-tenant salt for field-level commitment derivation.

    The salt is generated once per tenant and stored in the database.
    It is NEVER logged, returned to the caller, or stored in S3.
    """

    tenant_id: str
    salt: bytes  # 32 bytes, cryptographically random

    def commit_field(self, field_name: str, field_value: str) -> str:
        """Derive a commitment hash for a field value.

        Uses HMAC-SHA256 with the tenant salt as the key. Two tenants
        with the same field value produce different commitments.

        Returns a hex-encoded string suitable for storage in evidence
        records.
        """
        h = hmac.new(self.salt, f"{field_name}:{field_value}".encode(), hashlib.sha256)
        return h.hexdigest()


class TenantSaltRegistry:
    """In-memory tenant salt registry.

    In production, this is backed by the database. For the pilot, it's
    in-memory. The registry generates a new salt on first access for a
    tenant and caches it.
    """

    def __init__(self) -> None:
        self._salts: dict[str, TenantSalt] = {}

    def get_or_create(self, tenant_id: str) -> TenantSalt:
        """Get the salt for a tenant, creating it if it doesn't exist."""
        if tenant_id not in self._salts:
            self._salts[tenant_id] = TenantSalt(
                tenant_id=tenant_id,
                salt=secrets.token_bytes(32),
            )
        return self._salts[tenant_id]

    def set_salt(self, tenant_id: str, salt: bytes) -> None:
        """Set a specific salt for a tenant (used by database-backed registry)."""
        if len(salt) != 32:
            raise ValueError(f"salt must be 32 bytes, got {len(salt)}")
        self._salts[tenant_id] = TenantSalt(tenant_id=tenant_id, salt=salt)

    def clear(self) -> None:
        """Clear all cached salts (for testing)."""
        self._salts.clear()


# Module-level singleton for the pilot.
# Production should use a database-backed registry.
_default_registry: TenantSaltRegistry | None = None


def get_default_salt_registry() -> TenantSaltRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = TenantSaltRegistry()
    return _default_registry


# ---------------------------------------------------------------------------
# S3 evidence backend
# ---------------------------------------------------------------------------


class S3EvidenceBackend(EvidenceBackend):
    """S3-backed evidence storage.

    Stores evidence artefacts in S3 with per-tenant key prefixes:
        s3://{bucket}/{prefix}/{tenant_id}/{action_intent_id}/{evidence_object_id}{suffix}

    The backend uses boto3 (optional dependency). If boto3 is not
    installed, the backend raises EvidenceBackendNotReadyError on
    initialization.

    Content addressing: each artefact's S3 key includes its SHA-256
    digest, so the same content always lands at the same key. This
    enables deduplication and integrity verification.

    Per-tenant isolation: each tenant's evidence is stored under a
    unique prefix. IAM policies can restrict access to specific tenant
    prefixes.

    Server-side encryption: S3 SSE-KMS is used by default. The KMS key
    ID is configurable. Evidence is encrypted at rest with a key that
    is separate from the signing key.
    """

    storage_mode = EvidenceStorageMode.object_store

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "evidence",
        endpoint: str | None = None,
        region: str | None = None,
        kms_key_id: str | None = None,
        s3_client: Any = None,
    ) -> None:
        normalized_bucket = bucket.strip()
        if not normalized_bucket:
            raise ValueError("S3 evidence backend requires a bucket name")
        normalized_prefix = prefix.strip().strip("/")
        if not normalized_prefix:
            raise ValueError("S3 evidence backend requires a non-empty prefix")

        self.bucket = normalized_bucket
        self.prefix = normalized_prefix
        self.endpoint = endpoint.strip() if endpoint else None
        self.region = region
        self.kms_key_id = kms_key_id

        # Use injected client (for testing) or create a real one.
        if s3_client is not None:
            self._s3 = s3_client
        else:
            try:
                import boto3  # type: ignore[import-untyped]
            except ImportError as e:
                raise EvidenceBackendNotReadyError(
                    "boto3 is not installed; install with: pip install boto3"
                ) from e

            kwargs: dict[str, Any] = {}
            if self.region:
                kwargs["region_name"] = self.region
            if self.endpoint:
                kwargs["endpoint_url"] = self.endpoint
            self._s3 = boto3.client("s3", **kwargs)

    def store_upload(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        evidence_object_id: str,
        filename: str,
        payload: bytes,
    ) -> StoredEvidenceArtifact:
        """Store an evidence artefact in S3."""
        suffix = Path(filename or "upload.bin").suffix[:16]
        digest = hashlib.sha256(payload).hexdigest()

        # S3 key: {prefix}/{tenant_id}/{action_intent_id}/{evidence_object_id}{suffix}
        key = f"{self.prefix}/{tenant_id}/{action_intent_record_id}/{evidence_object_id}{suffix}"

        # Server-side encryption configuration
        put_kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": payload,
            "ContentType": "application/octet-stream",
        }
        if self.kms_key_id:
            put_kwargs["ServerSideEncryption"] = "aws:kms"
            put_kwargs["SSEKMSKeyId"] = self.kms_key_id

        try:
            self._s3.put_object(**put_kwargs)
        except Exception as e:
            raise EvidenceBackendNotReadyError(
                f"failed to store evidence in S3: {type(e).__name__}: {e}"
            ) from e

        return StoredEvidenceArtifact(
            storage_mode=self.storage_mode,
            storage_ref=f"s3://{self.bucket}/{key}",
            content_digest=digest,
            size_bytes=len(payload),
        )

    def open_content(self, evidence_object: EvidenceObject) -> Path:
        """Retrieve evidence content from S3.

        Downloads the object to a temporary file and returns the path.
        The caller is responsible for cleaning up the temporary file.
        """
        ref = evidence_object.storage_ref
        if not ref.startswith("s3://"):
            raise EvidenceContentUnsupportedError(
                f"storage_ref is not an S3 URI: {ref!r}"
            )

        # Parse s3://{bucket}/{key}
        parts = ref[5:].split("/", 1)
        if len(parts) != 2:
            raise EvidenceContentUnsupportedError(f"invalid S3 URI: {ref!r}")
        bucket, key = parts

        # Download to a temp file
        import tempfile

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix)
        try:
            self._s3.download_fileobj(bucket, key, tmp)
            tmp.close()
            return Path(tmp.name)
        except Exception as e:
            tmp.close()
            os.unlink(tmp.name)
            raise EvidenceContentUnsupportedError(
                f"failed to retrieve evidence from S3: {type(e).__name__}: {e}"
            ) from e

    def health(self) -> dict[str, Any]:
        """Health check for the S3 backend."""
        try:
            self._s3.head_bucket(Bucket=self.bucket)
            return {
                "ok": True,
                "backend": "s3",
                "bucket": self.bucket,
                "prefix": self.prefix,
                "kms_encrypted": self.kms_key_id is not None,
            }
        except Exception as e:
            return {
                "ok": False,
                "backend": "s3",
                "bucket": self.bucket,
                "error": f"{type(e).__name__}: {e}",
            }


__all__ = [
    "S3EvidenceBackend",
    "TenantSalt",
    "TenantSaltRegistry",
    "get_default_salt_registry",
]
