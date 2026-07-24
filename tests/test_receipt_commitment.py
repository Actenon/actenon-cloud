"""Tests for the receipt commitment layer.

Fable 5 Part 3D follow-up: "Commitment layer not yet wired into receipt
ingestion."

These tests verify:
  - PII-adjacent fields get commitment hashes
  - Same field value + different tenants → different commitments
  - Same field value + same tenant → same commitment (deterministic)
  - Non-PII fields (amount, currency, action_type) are NOT committed
  - None values are skipped
  - Verification detects tampering
"""

from __future__ import annotations

import unittest

from app.services.receipt_commitment import (
    COMMITTED_INDEX_FIELDS,
    commit_receipt_index_fields,
    verify_receipt_index_commitment,
)
from app.services.s3_evidence import TenantSaltRegistry


class TestCommitReceiptIndexFields(unittest.TestCase):
    """Tests for the commitment wiring into receipt_index."""

    def setUp(self):
        self.registry = TenantSaltRegistry()

    def test_committed_fields_set(self):
        """The committed fields are exactly the PII-adjacent account refs."""
        self.assertEqual(
            COMMITTED_INDEX_FIELDS,
            frozenset({"source_account_ref", "destination_account_ref"}),
        )

    def test_commitment_added_for_pii_fields(self):
        index = {
            "source_account_ref": "acct_abc123",
            "destination_account_ref": "acct_xyz789",
            "amount_minor": 2500,
            "currency": "GBP",
        }
        result = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        self.assertIn("source_account_ref_commitment", result)
        self.assertIn("destination_account_ref_commitment", result)
        # Cleartext preserved (for pilot operationability)
        self.assertEqual(result["source_account_ref"], "acct_abc123")
        self.assertEqual(result["destination_account_ref"], "acct_xyz789")
        # Non-PII fields NOT committed
        self.assertNotIn("amount_minor_commitment", result)
        self.assertNotIn("currency_commitment", result)

    def test_different_tenants_different_commitments(self):
        """Same account ref in two tenants → different commitments.

        This is the core privacy property: cross-tenant correlation is
        prevented because the same account reference produces different
        hashes in different tenants.
        """
        index = {"source_account_ref": "acct_shared"}
        commit_a = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        commit_b = commit_receipt_index_fields(
            index, tenant_id="tenant-b", registry=self.registry
        )
        self.assertNotEqual(
            commit_a["source_account_ref_commitment"],
            commit_b["source_account_ref_commitment"],
        )

    def test_same_tenant_same_commitment(self):
        """Same account ref + same tenant → same commitment (deterministic)."""
        index = {"source_account_ref": "acct_abc"}
        c1 = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        c2 = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        self.assertEqual(
            c1["source_account_ref_commitment"],
            c2["source_account_ref_commitment"],
        )

    def test_none_values_skipped(self):
        index = {
            "source_account_ref": None,
            "destination_account_ref": "acct_xyz",
        }
        result = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        # source_account_ref is None → no commitment added
        self.assertNotIn("source_account_ref_commitment", result)
        # destination_account_ref is present → commitment added
        self.assertIn("destination_account_ref_commitment", result)

    def test_input_not_modified(self):
        """The function returns a new dict; input is not mutated."""
        index = {"source_account_ref": "acct_abc"}
        original = dict(index)
        commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        self.assertEqual(index, original)

    def test_empty_index(self):
        result = commit_receipt_index_fields(
            {}, tenant_id="tenant-a", registry=self.registry
        )
        self.assertEqual(result, {})


class TestVerifyReceiptIndexCommitment(unittest.TestCase):
    """Tests for the commitment verification (audit path)."""

    def setUp(self):
        self.registry = TenantSaltRegistry()

    def test_verify_correct_commitment(self):
        index = {"source_account_ref": "acct_abc"}
        committed = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        self.assertTrue(
            verify_receipt_index_commitment(
                committed, tenant_id="tenant-a", registry=self.registry
            )
        )

    def test_verify_detects_tampered_cleartext(self):
        """If someone changes the cleartext but not the commitment, verify fails."""
        index = {"source_account_ref": "acct_abc"}
        committed = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        # Tamper: change cleartext but leave commitment
        committed["source_account_ref"] = "acct_EVIL"
        self.assertFalse(
            verify_receipt_index_commitment(
                committed, tenant_id="tenant-a", registry=self.registry
            )
        )

    def test_verify_detects_tampered_commitment(self):
        index = {"source_account_ref": "acct_abc"}
        committed = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        committed["source_account_ref_commitment"] = "evil_hash"
        self.assertFalse(
            verify_receipt_index_commitment(
                committed, tenant_id="tenant-a", registry=self.registry
            )
        )

    def test_verify_detects_missing_commitment(self):
        index = {"source_account_ref": "acct_abc"}
        # Has cleartext but no commitment
        self.assertFalse(
            verify_receipt_index_commitment(
                index, tenant_id="tenant-a", registry=self.registry
            )
        )

    def test_verify_skips_none_fields(self):
        """Fields that are None in both cleartext and commitment are skipped."""
        index = {"source_account_ref": None}
        self.assertTrue(
            verify_receipt_index_commitment(
                index, tenant_id="tenant-a", registry=self.registry
            )
        )

    def test_verify_wrong_tenant_fails(self):
        """Commitment derived for tenant-a fails verification against tenant-b."""
        index = {"source_account_ref": "acct_abc"}
        committed = commit_receipt_index_fields(
            index, tenant_id="tenant-a", registry=self.registry
        )
        self.assertFalse(
            verify_receipt_index_commitment(
                committed, tenant_id="tenant-b", registry=self.registry
            )
        )


if __name__ == "__main__":
    unittest.main()
