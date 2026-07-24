"""Commitment layer for receipt ingestion — per-tenant field commitments.

Fable 5 Part 3D follow-up: "Commitment layer not yet wired into receipt
ingestion."

The per-tenant salt registry (app/services/s3_evidence.py) exists but
was not called during receipt storage. This module wires it in.

What gets committed
-------------------

The receipt_index contains fields used for querying and correlation
across receipts. Two of these fields are PII-adjacent:

  - ``source_account_ref``      — the account money came from
  - ``destination_account_ref`` — the account money went to

These are operational references (not raw account numbers — they're
already opaque IDs like ``acct_abc123``). But they still allow
cross-tenant correlation: if two tenants both reference ``acct_abc123``,
an operator with database access can see that. The commitment layer
hashes these fields per-tenant so the same account reference produces
different commitment hashes in different tenants.

What does NOT get committed
---------------------------

  - ``receipt_payload`` — the raw kernel receipt is stored as-is because
    it must remain cryptographically verifiable. Modifying it would
    break the receipt signature.
  - ``kernel_receipt_digest`` — this is already a SHA-256 hash; it's
    not PII.
  - Fields like ``amount_minor``, ``currency``, ``action_type`` — these
    are not PII and need to be queryable in cleartext for operational
    dashboards.

Design
------

The commitment layer is opt-in per field. The list of committed fields
is defined in ``COMMITTED_INDEX_FIELDS``. Adding a field to this set
is a breaking change for existing receipts (their committed values will
change), so it requires a migration.

The committed value is stored alongside the cleartext value in the
receipt_index, with a ``_commitment`` suffix:

    {
        "source_account_ref": "acct_abc123",          # cleartext (for the pilot)
        "source_account_ref_commitment": "a1b2c3...",  # per-tenant commitment
    }

For the pilot, both are stored so operators can query by cleartext.
For production (GDPR Art. 17 compliance), the cleartext field should
be dropped, leaving only the commitment. The commitment is sufficient
for correlation WITHIN a tenant (same account → same commitment) but
prevents correlation ACROSS tenants (different salts → different
commitments for the same account).
"""

from __future__ import annotations

from typing import Any

from .s3_evidence import TenantSaltRegistry, get_default_salt_registry

# Fields in receipt_index that get per-tenant commitment hashes.
# Adding a field here is a breaking change for existing receipts.
# See module docstring for the rationale.
COMMITTED_INDEX_FIELDS: frozenset[str] = frozenset({
    "source_account_ref",
    "destination_account_ref",
})


def commit_receipt_index_fields(
    receipt_index: dict[str, Any],
    *,
    tenant_id: str,
    registry: TenantSaltRegistry | None = None,
) -> dict[str, Any]:
    """Add per-tenant commitment hashes for PII-adjacent index fields.

    For each field in COMMITTED_INDEX_FIELDS that is present and non-None
    in receipt_index, adds a ``{field}_commitment`` key containing the
    HMAC-SHA256 commitment.

    The original cleartext value is preserved (for pilot operationability).
    Production deployments that need GDPR Art. 17 compliance should drop
    the cleartext field after the commitment is computed.

    Args:
        receipt_index: The receipt index dict (from _build_receipt_index).
        tenant_id: The tenant ID for salt derivation.
        registry: Optional salt registry. Defaults to the module-level
                  singleton.

    Returns:
        A new dict with commitment fields added. The input dict is not
        modified.
    """
    if registry is None:
        registry = get_default_salt_registry()

    salt = registry.get_or_create(tenant_id)
    result = dict(receipt_index)

    for field in COMMITTED_INDEX_FIELDS:
        value = receipt_index.get(field)
        if value is not None:
            commitment = salt.commit_field(field, str(value))
            result[f"{field}_commitment"] = commitment

    return result


def verify_receipt_index_commitment(
    receipt_index: dict[str, Any],
    *,
    tenant_id: str,
    registry: TenantSaltRegistry | None = None,
) -> bool:
    """Verify that the commitment fields in receipt_index are correct.

    Returns True if all commitment fields match the cleartext values
    (re-derived with the tenant's salt). Returns False if any commitment
    is missing or does not match.

    This is used by the audit path to confirm that receipts were stored
    with correct commitments and have not been tampered with.
    """
    if registry is None:
        registry = get_default_salt_registry()

    salt = registry.get_or_create(tenant_id)

    for field in COMMITTED_INDEX_FIELDS:
        value = receipt_index.get(field)
        commitment = receipt_index.get(f"{field}_commitment")

        if value is None and commitment is None:
            continue

        if value is None or commitment is None:
            return False

        expected = salt.commit_field(field, str(value))
        if commitment != expected:
            return False

    return True


__all__ = [
    "COMMITTED_INDEX_FIELDS",
    "commit_receipt_index_fields",
    "verify_receipt_index_commitment",
]
