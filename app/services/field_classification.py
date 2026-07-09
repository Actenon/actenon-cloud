"""Field-classification layer: prevent PHI/PII from entering the immutable
hash-chained record.

The immutable receipt_payload is replaced with a commitment version:
  - Sensitive fields (patient_name, ssn, diagnosis, free-text notes) are
    replaced with sha256(canonical_json(value) + per-tenant-salt) commitments.
  - The raw values go to the mutable EvidenceStore under a separate key,
    referenced by commitment hash — so a GDPR Art.17 erasure deletes the
    payload WITHOUT breaking the hash chain.
  - The commitment still proves the params matched (given the params,
    recompute the commitment and compare).

Default policy: params_visibility = "commitment" (all params committed).
Plaintext must be explicitly opted in per action type.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Sensitive field names that must NEVER appear in plaintext in the immutable record
SENSITIVE_FIELDS = frozenset({
    "patient_name", "ssn", "diagnosis", "note", "notes",
    "free_text", "description", "reason", "body", "content",
    "medical_record_number", "mrn", "dob", "date_of_birth",
    "phone", "email", "address", "zip_code", "postal_code",
})

# Fields that are safe to keep in plaintext (structural, not PII)
SAFE_FIELDS = frozenset({
    "amount_minor", "currency", "action_type", "workflow_key",
    "source_account_ref", "destination_account_ref", "destination_country",
    "invoice_number", "vendor_name", "payee_reference",
    "intent_id", "receipt_id", "occurred_at", "outcome",
    "proof_nonce", "audience", "scope", "action_intent_digest",
    "contract", "version_ref", "contract_family",
    "risk_tier", "evidence_present",
})


def _commit(value: Any, salt: str) -> str:
    """Compute a salted commitment: sha256(canonical_json(value) + salt)."""
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((canonical + salt).encode("utf-8")).hexdigest()


def classify_params(
    params: dict[str, Any],
    *,
    tenant_salt: str,
    params_visibility: str = "commitment",
) -> tuple[dict[str, Any], dict[str, str]]:
    """Classify params into committed (immutable-safe) + raw (mutable evidence).

    Returns (committed_params, raw_for_evidence) where:
      - committed_params: safe for the hash-chained record (commitments for sensitive)
      - raw_for_evidence: original values keyed by commitment hash, for the mutable store

    If params_visibility == "plaintext", all params are kept in plaintext
    (opt-in only, for non-sensitive action types).
    """
    if params_visibility == "plaintext":
        return dict(params), {}

    committed: dict[str, Any] = {}
    raw_for_evidence: dict[str, str] = {}

    for key, value in params.items():
        if key in SENSITIVE_FIELDS or key not in SAFE_FIELDS:
            # Commit this field
            commitment = _commit(value, tenant_salt)
            committed[key] = {"_commitment": commitment}
            if isinstance(value, (str, int, float, bool)):
                raw_for_evidence[commitment] = value
            else:
                raw_for_evidence[commitment] = json.dumps(value, default=str)
        else:
            # Safe field — keep in plaintext
            committed[key] = value

    return committed, raw_for_evidence


def verify_commitment(
    params: dict[str, Any],
    committed_params: dict[str, Any],
    *,
    tenant_salt: str,
) -> bool:
    """Verify that params match the committed params.

    For each committed field, recompute the commitment and compare.
    Returns True if all committed fields match.
    """
    for key, value in params.items():
        committed_value = committed_params.get(key)
        if isinstance(committed_value, dict) and "_commitment" in committed_value:
            expected = _commit(value, tenant_salt)
            if expected != committed_value["_commitment"]:
                return False
    return True


__all__ = [
    "SENSITIVE_FIELDS",
    "SAFE_FIELDS",
    "classify_params",
    "verify_commitment",
]
