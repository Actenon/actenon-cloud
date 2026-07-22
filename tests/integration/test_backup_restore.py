"""B10 integration: backup → destroy → restore preserves the hash chain.

This test exercises the disaster-recovery path documented in
``BACKUP_RESTORE_ASSUMPTIONS.md``: the database file is the source of
truth for the transparency ledger and the action-intent / proof /
receipt records. Restoring from a file backup must:

1. Preserve the append-chain hash chain (``TransparencyLogService.audit_integrity()``).
2. Preserve action-intent records so operators can continue reconciliation.

The test is filesystem-level (sqlite only) because that's the only way
to exercise the actual backup/restore lifecycle without a managed
PostgreSQL sidecar. The hash-chain verification logic is identical
across backends.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  — register all ORM tables on Base.metadata
from app.database import Base
from app.models import (
    ActionIntentRecord,
    ContractValidationStatus,
    DecisionState,
    FinanceProfile,
    IssuedProof,
    ProofIssuanceStatus,
    ProofKind,
    ReceiptRecord,
    ReceiptState,
    Tenant,
    TenantStatus,
    TrustTier,
)
from app.services.transparency_log import TransparencyLogService


def _digest(value: str) -> dict[str, str]:
    return {
        "algorithm": "sha-256",
        "canonicalization": "RFC8785-JCS",
        "value": value,
    }


def _make_tenant(tenant_id: str = "tenant-backup") -> Tenant:
    return Tenant(
        tenant_id=tenant_id,
        display_name="Backup/Restore Tenant",
        status=TenantStatus.active,
        finance_profile=FinanceProfile.payments,
    )


def _make_action_intent(
    *,
    tenant_id: str,
    action_intent_record_id: str,
    intent_id: str,
    amount_minor: int,
) -> ActionIntentRecord:
    return ActionIntentRecord(
        action_intent_record_id=action_intent_record_id,
        tenant_id=tenant_id,
        submission_id=f"submission-{action_intent_record_id}",
        idempotency_key=f"idemp-{action_intent_record_id}",
        requested_by_principal_type="user",
        requested_by_principal_id="ops-alice",
        workflow_key="payments.standard",
        external_action_intent_id=intent_id,
        contract_family="action_intent",
        contract_version_ref="open_execution_kernel.action_intent.finance.v1alpha1",
        contract_validation_status=ContractValidationStatus.valid,
        action_intent_digest="a" * 64,
        action_intent_payload={
            "intent_id": intent_id,
            "workflow_key": "payments.standard",
            "action_type": "transfer",
            "amount_minor": amount_minor,
            "currency": "USD",
        },
        decision_state=DecisionState.allow,
        decision_reason="backup/restore test allow",
    )


def _make_proof(
    *,
    tenant_id: str,
    action_intent_record_id: str,
    issued_proof_id: str,
) -> IssuedProof:
    return IssuedProof(
        issued_proof_id=issued_proof_id,
        tenant_id=tenant_id,
        action_intent_record_id=action_intent_record_id,
        signing_key_reference_id=None,
        proof_kind=ProofKind.pccb,
        status=ProofIssuanceStatus.issued,
        issuer_name="actenon-cloud",
        issuer_uri="https://actenon.example",
        trust_tier=TrustTier.development_local,
        audience="finance-ops.internal",
        scope=["finance.transfer.release"],
        scope_hash="b" * 64,
        nonce="c" * 32,
        action_intent_digest="a" * 64,
        proof_payload={"binding": {"audience": "finance-ops.internal"}},
        proof_payload_digest="d" * 64,
        signature="dummy-signature",
        issued_by_principal_type="user",
        issued_by_principal_id="issuer-operator-001",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )


def _make_receipt(
    *,
    tenant_id: str,
    action_intent_record_id: str,
    issued_proof_id: str,
    receipt_id: str,
    kernel_receipt_digest: str,
) -> ReceiptRecord:
    return ReceiptRecord(
        receipt_id=receipt_id,
        tenant_id=tenant_id,
        action_intent_record_id=action_intent_record_id,
        issued_proof_id=issued_proof_id,
        contract_family="receipt",
        contract_version_ref="open_execution_kernel.receipt.finance.v1alpha1",
        contract_validation_status="valid",
        external_receipt_id=f"ext-{receipt_id}",
        receipt_type="execution_result",
        outcome="succeeded",
        receipt_timestamp=datetime.now(UTC),
        kernel_receipt_digest=kernel_receipt_digest,
        received_by_principal_type="system",
        received_by_principal_id="receipt-ingestor-001",
        receipt_state=ReceiptState.reconciled,
    )


def _populate(session: Session, log_identity: dict[str, object]) -> None:
    """Seed tenant, action intents, proofs, receipts, and the transparency log."""
    tenant = _make_tenant()
    session.add(tenant)
    session.flush()

    intent_a = _make_action_intent(
        tenant_id=tenant.tenant_id,
        action_intent_record_id="intent-backup-001",
        intent_id="intent-backup-001",
        amount_minor=1000,
    )
    intent_b = _make_action_intent(
        tenant_id=tenant.tenant_id,
        action_intent_record_id="intent-backup-002",
        intent_id="intent-backup-002",
        amount_minor=2500,
    )
    session.add_all([intent_a, intent_b])
    session.flush()

    proof_a = _make_proof(
        tenant_id=tenant.tenant_id,
        action_intent_record_id=intent_a.action_intent_record_id,
        issued_proof_id="proof-backup-001",
    )
    proof_b = _make_proof(
        tenant_id=tenant.tenant_id,
        action_intent_record_id=intent_b.action_intent_record_id,
        issued_proof_id="proof-backup-002",
    )
    session.add_all([proof_a, proof_b])
    session.flush()

    receipt_a = _make_receipt(
        tenant_id=tenant.tenant_id,
        action_intent_record_id=intent_a.action_intent_record_id,
        issued_proof_id=proof_a.issued_proof_id,
        receipt_id="receipt-backup-001",
        kernel_receipt_digest="e" * 63 + "1",
    )
    receipt_b = _make_receipt(
        tenant_id=tenant.tenant_id,
        action_intent_record_id=intent_b.action_intent_record_id,
        issued_proof_id=proof_b.issued_proof_id,
        receipt_id="receipt-backup-002",
        kernel_receipt_digest="e" * 63 + "2",
    )
    session.add_all([receipt_a, receipt_b])
    session.commit()

    # Append the receipt digests to the transparency log so the append-chain
    # hash chain is populated. This is the "ledger" the test will verify.
    log = TransparencyLogService(session, log_identity=log_identity)
    log.append_receipt_digest(_digest("1" * 64))
    log.append_receipt_digest(_digest("2" * 64))
    session.commit()


def test_backup_restore_preserves_ledger_and_action_intents(tmp_path: Path) -> None:
    """Backup → destroy → restore preserves the hash chain and action intents."""
    db_path = tmp_path / "control-plane.db"
    backup_path = tmp_path / "control-plane.db.bak"
    database_url = f"sqlite+pysqlite:///{db_path}"
    log_identity = {
        "id": "log-backup-test",
        "type": "service",
        "display_name": "Backup Test Transparency Log",
    }

    # 1. Create the DB and seed it with data + ledger entries.
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine, expire_on_commit=False) as session:
        _populate(session, log_identity=log_identity)

    # Capture pre-backup state for post-restore comparison.
    with Session(bind=engine, expire_on_commit=False) as session:
        log = TransparencyLogService(session, log_identity=log_identity)
        pre_backup_report = log.audit_integrity()
        pre_backup_action_intents = list(session.scalars(select(ActionIntentRecord)))
        pre_backup_proofs = list(session.scalars(select(IssuedProof)))
        pre_backup_receipts = list(session.scalars(select(ReceiptRecord)))
    assert pre_backup_report.ok is True, (
        f"pre-backup ledger must be healthy: {pre_backup_report.error_codes}"
    )
    assert pre_backup_report.leaf_count == 2
    assert len(pre_backup_action_intents) == 2
    assert len(pre_backup_proofs) == 2
    assert len(pre_backup_receipts) == 2

    # 2. Back up the DB file — must release the SQLite handle first.
    engine.dispose()
    shutil.copy2(db_path, backup_path)
    assert backup_path.is_file(), "backup file must exist after copy"
    assert backup_path.stat().st_size > 0, "backup file must be non-empty"

    # 3. Destroy the original DB.
    db_path.unlink()
    assert not db_path.exists(), "original DB file must be destroyed"

    # 4. Restore from backup.
    shutil.copy2(backup_path, db_path)
    assert db_path.is_file(), "restored DB file must exist"

    # 5. Re-open the restored DB and verify the hash chain still passes.
    #    TransparencyLogService.audit_integrity() is the cloud's ledger.verify()
    #    — it walks the append-chain and Merkle checkpoints and reports any
    #    mismatch.
    restored_engine = create_engine(database_url)
    try:
        with Session(bind=restored_engine, expire_on_commit=False) as session:
            log = TransparencyLogService(session, log_identity=log_identity)
            post_restore_report = log.audit_integrity()
            assert post_restore_report.ok is True, (
                "restored ledger must pass integrity audit: "
                f"{post_restore_report.error_codes}"
            )
            assert post_restore_report.leaf_count == pre_backup_report.leaf_count, (
                "restored ledger leaf count must match pre-backup"
            )

            # 6. Verify action intents are still readable, with the same IDs
            #    and digest values. This proves the restored DB is usable
            #    for ongoing reconciliation.
            restored_action_intents = list(session.scalars(select(ActionIntentRecord)))
            assert len(restored_action_intents) == 2
            restored_intent_ids = {
                record.action_intent_record_id for record in restored_action_intents
            }
            assert restored_intent_ids == {
                record.action_intent_record_id for record in pre_backup_action_intents
            }
            for record in restored_action_intents:
                assert record.action_intent_digest == "a" * 64
                assert record.tenant_id == "tenant-backup"
                assert record.contract_validation_status == ContractValidationStatus.valid
                assert record.decision_state == DecisionState.allow

            # Proofs and receipts must also survive the round-trip.
            restored_proofs = list(session.scalars(select(IssuedProof)))
            assert len(restored_proofs) == 2
            restored_receipts = list(session.scalars(select(ReceiptRecord)))
            assert len(restored_receipts) == 2
            assert {r.receipt_id for r in restored_receipts} == {
                "receipt-backup-001",
                "receipt-backup-002",
            }
    finally:
        restored_engine.dispose()
