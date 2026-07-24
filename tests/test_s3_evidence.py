"""Tests for the S3 evidence backend and per-tenant salt registry.

Tests use mock S3 clients — no real AWS calls are made.
"""

from __future__ import annotations

import hashlib
import os
import unittest
from unittest.mock import MagicMock

from app.services.evidence_backends import (
    EvidenceBackendNotReadyError,
    StoredEvidenceArtifact,
)
from app.services.s3_evidence import (
    S3EvidenceBackend,
    TenantSalt,
    TenantSaltRegistry,
    get_default_salt_registry,
)


class TestTenantSalt(unittest.TestCase):
    """Tests for the per-tenant salt and field commitment."""

    def test_salt_is_32_bytes(self):
        reg = TenantSaltRegistry()
        salt = reg.get_or_create("tenant-a")
        self.assertEqual(len(salt.salt), 32)

    def test_same_tenant_gets_same_salt(self):
        reg = TenantSaltRegistry()
        s1 = reg.get_or_create("tenant-a")
        s2 = reg.get_or_create("tenant-a")
        self.assertEqual(s1.salt, s2.salt)

    def test_different_tenants_get_different_salts(self):
        """Two tenants with the same field value produce different commitments."""
        reg = TenantSaltRegistry()
        salt_a = reg.get_or_create("tenant-a")
        salt_b = reg.get_or_create("tenant-b")

        self.assertNotEqual(salt_a.salt, salt_b.salt)

        # Same field value, different salts → different commitments
        commit_a = salt_a.commit_field("customer_email", "alice@example.com")
        commit_b = salt_b.commit_field("customer_email", "alice@example.com")
        self.assertNotEqual(commit_a, commit_b)

    def test_same_tenant_same_field_same_commitment(self):
        """Same tenant + same field → same commitment (deterministic)."""
        reg = TenantSaltRegistry()
        salt = reg.get_or_create("tenant-a")

        c1 = salt.commit_field("customer_email", "alice@example.com")
        c2 = salt.commit_field("customer_email", "alice@example.com")
        self.assertEqual(c1, c2)

    def test_different_fields_different_commitments(self):
        """Same value, different field names → different commitments."""
        reg = TenantSaltRegistry()
        salt = reg.get_or_create("tenant-a")

        c1 = salt.commit_field("customer_email", "alice@example.com")
        c2 = salt.commit_field("billing_email", "alice@example.com")
        self.assertNotEqual(c1, c2)

    def test_set_salt_explicit(self):
        """Database-backed registry can set a specific salt."""
        reg = TenantSaltRegistry()
        explicit_salt = bytes(range(32))
        reg.set_salt("tenant-x", explicit_salt)
        salt = reg.get_or_create("tenant-x")
        self.assertEqual(salt.salt, explicit_salt)

    def test_set_salt_rejects_wrong_length(self):
        reg = TenantSaltRegistry()
        with self.assertRaises(ValueError):
            reg.set_salt("tenant-x", b"too_short")

    def test_clear(self):
        reg = TenantSaltRegistry()
        reg.get_or_create("tenant-a")
        reg.clear()
        # After clear, a new salt is generated
        salt = reg.get_or_create("tenant-a")
        self.assertEqual(len(salt.salt), 32)


class TestS3EvidenceBackend(unittest.TestCase):
    """Tests for the S3 evidence backend (with mock S3 client)."""

    def _make_mock_s3(self) -> MagicMock:
        """Create a mock S3 client that mimics boto3's S3 client."""
        client = MagicMock()
        client.put_object.return_value = {"ETag": "mock-etag"}
        client.head_bucket.return_value = {}
        return client

    def test_store_upload_happy_path(self):
        mock_s3 = self._make_mock_s3()
        backend = S3EvidenceBackend(
            bucket="evidence-bucket",
            prefix="evidence",
            s3_client=mock_s3,
        )

        payload = b'{"action": "payment.refund", "amount": 2500}'
        result = backend.store_upload(
            tenant_id="tenant-acme",
            action_intent_record_id="intent-123",
            evidence_object_id="evidence-456",
            filename="receipt.json",
            payload=payload,
        )

        self.assertIsInstance(result, StoredEvidenceArtifact)
        self.assertEqual(result.storage_mode.value, "object_store")
        self.assertEqual(
            result.storage_ref,
            "s3://evidence-bucket/evidence/tenant-acme/intent-123/evidence-456.json",
        )
        self.assertEqual(result.content_digest, hashlib.sha256(payload).hexdigest())
        self.assertEqual(result.size_bytes, len(payload))

        # Verify the S3 put_object was called correctly
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args.kwargs
        self.assertEqual(call_kwargs["Bucket"], "evidence-bucket")
        self.assertEqual(call_kwargs["Key"], "evidence/tenant-acme/intent-123/evidence-456.json")
        self.assertEqual(call_kwargs["Body"], payload)

    def test_store_upload_with_kms_encryption(self):
        mock_s3 = self._make_mock_s3()
        backend = S3EvidenceBackend(
            bucket="evidence-bucket",
            prefix="evidence",
            kms_key_id="arn:aws:kms:eu-west-2:123:key/abc",
            s3_client=mock_s3,
        )

        backend.store_upload(
            tenant_id="tenant-a",
            action_intent_record_id="intent-1",
            evidence_object_id="ev-1",
            filename="data.bin",
            payload=b"test",
        )

        call_kwargs = mock_s3.put_object.call_args.kwargs
        self.assertEqual(call_kwargs["ServerSideEncryption"], "aws:kms")
        self.assertEqual(call_kwargs["SSEKMSKeyId"], "arn:aws:kms:eu-west-2:123:key/abc")

    def test_store_upload_without_kms(self):
        mock_s3 = self._make_mock_s3()
        backend = S3EvidenceBackend(
            bucket="evidence-bucket",
            prefix="evidence",
            s3_client=mock_s3,
        )

        backend.store_upload(
            tenant_id="t", action_intent_record_id="i", evidence_object_id="e",
            filename="f.bin", payload=b"x",
        )

        call_kwargs = mock_s3.put_object.call_args.kwargs
        self.assertNotIn("ServerSideEncryption", call_kwargs)
        self.assertNotIn("SSEKMSKeyId", call_kwargs)

    def test_store_upload_s3_failure_wraps_error(self):
        mock_s3 = self._make_mock_s3()
        mock_s3.put_object.side_effect = RuntimeError("network error")
        backend = S3EvidenceBackend(
            bucket="evidence-bucket", prefix="evidence", s3_client=mock_s3,
        )

        with self.assertRaises(EvidenceBackendNotReadyError) as ctx:
            backend.store_upload(
                tenant_id="t", action_intent_record_id="i", evidence_object_id="e",
                filename="f.bin", payload=b"x",
            )
        self.assertIn("failed to store evidence in S3", str(ctx.exception))

    def test_per_tenant_isolation(self):
        """Evidence for different tenants goes to different S3 keys."""
        mock_s3 = self._make_mock_s3()
        backend = S3EvidenceBackend(
            bucket="evidence-bucket", prefix="evidence", s3_client=mock_s3,
        )

        backend.store_upload(
            tenant_id="tenant-a", action_intent_record_id="intent-1",
            evidence_object_id="ev-1", filename="a.json", payload=b"{}",
        )
        backend.store_upload(
            tenant_id="tenant-b", action_intent_record_id="intent-1",
            evidence_object_id="ev-1", filename="b.json", payload=b"{}",
        )

        keys = [call.kwargs["Key"] for call in mock_s3.put_object.call_args_list]
        self.assertTrue(any("tenant-a" in k for k in keys))
        self.assertTrue(any("tenant-b" in k for k in keys))
        # Tenant A's evidence must NOT be in Tenant B's key prefix
        self.assertFalse(any("tenant-b/tenant-a" in k for k in keys))

    def test_health_ok(self):
        mock_s3 = self._make_mock_s3()
        backend = S3EvidenceBackend(
            bucket="evidence-bucket", prefix="evidence", s3_client=mock_s3,
        )
        result = backend.health()
        self.assertTrue(result["ok"])
        self.assertEqual(result["backend"], "s3")
        self.assertEqual(result["bucket"], "evidence-bucket")

    def test_health_failure(self):
        mock_s3 = self._make_mock_s3()
        mock_s3.head_bucket.side_effect = RuntimeError("access denied")
        backend = S3EvidenceBackend(
            bucket="evidence-bucket", prefix="evidence", s3_client=mock_s3,
        )
        result = backend.health()
        self.assertFalse(result["ok"])
        self.assertIn("access denied", result["error"])

    def test_empty_bucket_rejected(self):
        with self.assertRaises(ValueError):
            S3EvidenceBackend(bucket="", prefix="evidence", s3_client=self._make_mock_s3())

    def test_empty_prefix_rejected(self):
        with self.assertRaises(ValueError):
            S3EvidenceBackend(bucket="bucket", prefix="", s3_client=self._make_mock_s3())


class TestDefaultSaltRegistry(unittest.TestCase):
    """Tests for the module-level salt registry singleton."""

    def test_singleton(self):
        reg1 = get_default_salt_registry()
        reg2 = get_default_salt_registry()
        self.assertIs(reg1, reg2)

    def test_get_or_create(self):
        reg = get_default_salt_registry()
        salt = reg.get_or_create("test-tenant")
        self.assertEqual(len(salt.salt), 32)


if __name__ == "__main__":
    unittest.main()
