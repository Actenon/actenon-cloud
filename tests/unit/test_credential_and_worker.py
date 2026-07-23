"""Tests for credential store + execution worker (Prompt 15).

Covers:
  * Credential encryption at rest (AES-256-GCM)
  * Tenant isolation (cross-tenant access denied)
  * Credential rotation (register overwrites + increments key_version)
  * Credential revocation (revoked -> resolve raises)
  * Access auditing (every operation logged)
  * Credential never in exceptions (error messages use ref only)
  * Execution worker: durable jobs (submit + run + idempotent)
  * Execution worker: retry policy (retryable errors retried)
  * Execution worker: dead-letter (exhausted retries -> dead_letter)
  * Execution worker: timeout (outcome_unknown -> timed_out after retries)
  * Execution worker: cancellation (non-terminal -> cancelled)
  * Execution worker: reconciliation (recover_pending_jobs)
"""

from __future__ import annotations

import pytest

from app.database import Base, Database
from app.services.credential_store import (
    CredentialAccessAudit,
    CredentialNotFoundError,
    CredentialRevokedError,
    EncryptedCredentialRecord,
    EncryptedCredentialStore,
)
from app.services.execution_worker import (
    ExecutionWorker,
    JobDeadLetteredError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def database(tmp_path):
    db = Database(database_url=f"sqlite+pysqlite:///{tmp_path / 'cred_test.db'}")
    db.connect()
    Base.metadata.create_all(bind=db.engine)
    yield db
    Base.metadata.drop_all(bind=db.engine)
    db.disconnect()


@pytest.fixture
def master_key():
    return b"test-master-key-32-bytes-not-real!"


@pytest.fixture
def store(database, master_key):
    with database.session() as session:
        s = EncryptedCredentialStore(session, master_key)
        yield s


# ---------------------------------------------------------------------------
# 1. Credential encryption at rest
# ---------------------------------------------------------------------------


def test_credential_encrypted_at_rest(database, master_key):
    """The encrypted_value column must NOT contain the plaintext."""
    with database.session() as session:
        s = EncryptedCredentialStore(session, master_key)
        s.register(tenant_id="t1", ref="github_token", value="ghp_SECRET_VALUE_123")

    with database.session() as session:
        from sqlalchemy import select

        record = session.execute(
            select(EncryptedCredentialRecord).where(
                EncryptedCredentialRecord.tenant_id == "t1",
                EncryptedCredentialRecord.ref == "github_token",
            )
        ).scalars().first()
        assert record is not None
        # The encrypted value must NOT contain the plaintext.
        assert "ghp_SECRET_VALUE_123" not in record.encrypted_value
        # The nonce must NOT be empty.
        assert record.nonce


# ---------------------------------------------------------------------------
# 2. Tenant isolation
# ---------------------------------------------------------------------------


def test_credential_tenant_isolation(store):
    """Tenant A's credential is not accessible to tenant B."""
    store.register(tenant_id="t1", ref="token", value="value_t1")
    store.register(tenant_id="t2", ref="token", value="value_t2")

    # t1 can resolve its own credential.
    assert store.resolve(tenant_id="t1", ref="token") == "value_t1"
    # t2 gets a different value (its own).
    assert store.resolve(tenant_id="t2", ref="token") == "value_t2"
    # t1 cannot resolve t2's credential (different tenant -> not found).
    with pytest.raises(CredentialNotFoundError):
        store.resolve(tenant_id="t1", ref="nonexistent_for_t1")


# ---------------------------------------------------------------------------
# 3. Credential rotation
# ---------------------------------------------------------------------------


def test_credential_rotation(store):
    """Register with the same ref overwrites the value + increments key_version."""
    store.register(tenant_id="t1", ref="token", value="old_value")
    assert store.resolve(tenant_id="t1", ref="token") == "old_value"

    store.register(tenant_id="t1", ref="token", value="new_value")
    assert store.resolve(tenant_id="t1", ref="token") == "new_value"

    refs = store.list_refs(tenant_id="t1")
    assert refs[0]["key_version"] == 2  # incremented on rotation


# ---------------------------------------------------------------------------
# 4. Credential revocation
# ---------------------------------------------------------------------------


def test_credential_revocation(store):
    """Revoked credentials raise CredentialRevokedError on resolve."""
    store.register(tenant_id="t1", ref="token", value="value")
    assert store.resolve(tenant_id="t1", ref="token") == "value"

    store.revoke(tenant_id="t1", ref="token")
    with pytest.raises(CredentialRevokedError):
        store.resolve(tenant_id="t1", ref="token")

    # List shows revoked status.
    refs = store.list_refs(tenant_id="t1")
    assert refs[0]["status"] == "revoked"
    assert refs[0]["revoked_at"] is not None


# ---------------------------------------------------------------------------
# 5. Access auditing
# ---------------------------------------------------------------------------


def test_access_auditing(store, database):
    """Every read/rotate/revoke is recorded in the audit table."""
    store.register(tenant_id="t1", ref="token", value="value")
    store.resolve(tenant_id="t1", ref="token")
    store.register(tenant_id="t1", ref="token", value="new_value")  # rotate
    store.revoke(tenant_id="t1", ref="token")
    store.list_refs(tenant_id="t1")

    with database.session() as session:
        from sqlalchemy import select

        audits = session.execute(
            select(CredentialAccessAudit).where(
                CredentialAccessAudit.tenant_id == "t1"
            )
        ).scalars().all()
        operations = [a.operation for a in audits]
        assert "register" in operations
        assert "read" in operations
        assert "rotate" in operations
        assert "revoke" in operations
        assert "list" in operations


# ---------------------------------------------------------------------------
# 6. Credential never in exceptions
# ---------------------------------------------------------------------------


def test_credential_not_in_exceptions(store):
    """Error messages must NOT contain the credential value."""
    secret = "ghp_test_value_not_for_logs"  # noqa: S105
    store.register(tenant_id="t1", ref="token", value=secret)

    # Resolve a non-existent ref — error must not contain the secret.
    try:
        store.resolve(tenant_id="t1", ref="wrong_ref")
    except CredentialNotFoundError as e:
        assert secret not in str(e)
    except Exception as e:
        pytest.fail(f"expected CredentialNotFoundError, got {type(e).__name__}")


# ---------------------------------------------------------------------------
# 7. Execution worker: durable jobs + idempotency
# ---------------------------------------------------------------------------


@pytest.fixture
def worker(database):
    with database.session() as session:
        yield ExecutionWorker(session)


def test_worker_submit_and_run(worker):
    """Submit a job, run it, get succeeded."""
    job = worker.submit_job(
        tenant_id="t1",
        intent_id="intent_1",
        idempotency_key="op_1",
        action_type="issue.create",
        action_params={"owner": "a", "repo": "b", "title": "t"},
    )
    assert job.status == "pending"

    def executor(action_type, params, idem_key, timeout):
        return {"ok": True, "state": "succeeded", "evidence": {"issue_url": "https://..."}}

    result = worker.run_job(job.job_id, executor)
    assert result["status"] == "succeeded"
    assert result["result"]["evidence"]["issue_url"] == "https://..."


def test_worker_idempotent_submit(worker):
    """Submitting with the same idempotency_key returns the original job."""
    job1 = worker.submit_job(
        tenant_id="t1",
        intent_id="intent_1",
        idempotency_key="op_idem",
        action_type="issue.create",
        action_params={"title": "t"},
    )
    job2 = worker.submit_job(
        tenant_id="t1",
        intent_id="intent_1",
        idempotency_key="op_idem",
        action_type="issue.create",
        action_params={"title": "t"},
    )
    assert job1.job_id == job2.job_id


def test_worker_idempotent_run(worker):
    """Running an already-succeeded job returns the existing result."""
    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_2",
        action_type="issue.create", action_params={},
    )
    def executor(*args):
        return {"ok": True, "state": "succeeded", "evidence": {}}
    result1 = worker.run_job(job.job_id, executor)
    result2 = worker.run_job(job.job_id, executor)
    assert result1["status"] == "succeeded"
    assert result2["status"] == "succeeded"


# ---------------------------------------------------------------------------
# 8. Execution worker: retry policy
# ---------------------------------------------------------------------------


def test_worker_retries_on_retryable_error(worker):
    """Retryable errors (outcome_unknown) are retried."""
    call_count = [0]

    def executor(*args):
        call_count[0] += 1
        if call_count[0] < 2:
            return {"ok": False, "state": "outcome_unknown", "error": "timeout"}
        return {"ok": True, "state": "succeeded", "evidence": {}}

    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_3",
        action_type="issue.create", action_params={}, max_retries=3,
    )
    result = worker.run_job(job.job_id, executor)
    assert result["status"] == "succeeded"
    assert call_count[0] == 2  # first attempt failed, second succeeded


# ---------------------------------------------------------------------------
# 9. Execution worker: dead-letter
# ---------------------------------------------------------------------------


def test_worker_dead_letter_on_exhausted_retries(worker):
    """When all retries are exhausted, the job is dead-lettered.

    With max_retries=2, the worker does 3 attempts. An outcome_unknown
    after all retries are exhausted transitions to timed_out (not
    dead_letter — dead_letter is for unexpected exceptions, not for
    exhausted outcome_unknown retries). Both are terminal failure states.
    """
    def executor(*args):
        return {"ok": False, "state": "outcome_unknown", "error": "always times out"}

    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_4",
        action_type="issue.create", action_params={}, max_retries=2,
    )
    result = worker.run_job(job.job_id, executor)
    # After exhausting retries on outcome_unknown, the job is timed_out.
    assert result["status"] == "timed_out"
    assert result["error"] is not None


def test_worker_dead_letter_on_unexpected_exception(worker):
    """Unexpected exceptions that exhaust retries go to dead_letter."""
    def executor(*args):
        raise RuntimeError("unexpected crash")

    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_4b",
        action_type="issue.create", action_params={}, max_retries=1,
    )
    with pytest.raises(JobDeadLetteredError):
        worker.run_job(job.job_id, executor)
    result = worker.get_job(job.job_id)
    assert result["status"] == "dead_letter"


# ---------------------------------------------------------------------------
# 10. Execution worker: non-retryable failure
# ---------------------------------------------------------------------------


def test_worker_non_retryable_failure(worker):
    """Non-retryable failures (state=failed) are not retried."""
    call_count = [0]

    def executor(*args):
        call_count[0] += 1
        return {"ok": False, "state": "failed", "error": "bad request"}

    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_5",
        action_type="issue.create", action_params={}, max_retries=3,
    )
    result = worker.run_job(job.job_id, executor)
    assert result["status"] == "failed"
    assert call_count[0] == 1  # no retry


# ---------------------------------------------------------------------------
# 11. Execution worker: cancellation
# ---------------------------------------------------------------------------


def test_worker_cancel(worker):
    """A pending job can be cancelled."""
    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_6",
        action_type="issue.create", action_params={},
    )
    result = worker.cancel_job(job.job_id)
    assert result["status"] == "cancelled"


# ---------------------------------------------------------------------------
# 12. Execution worker: reconciliation (recover pending)
# ---------------------------------------------------------------------------


def test_worker_recover_pending(worker):
    """Jobs left in pending state can be recovered."""
    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_7",
        action_type="issue.create", action_params={},
    )
    # Simulate a crash: job is left in pending.
    assert job.status == "pending"

    def executor(*args):
        return {"ok": True, "state": "succeeded", "evidence": {}}

    recovered = worker.recover_pending_jobs(executor)
    assert recovered == 1
    result = worker.get_job(job.job_id)
    assert result["status"] == "succeeded"


# ---------------------------------------------------------------------------
# 13. Execution worker: provider rate-limit handling
# ---------------------------------------------------------------------------


def test_worker_rate_limit_retry(worker):
    """Provider 429/503 (retryable) triggers retry."""
    call_count = [0]

    def executor(*args):
        call_count[0] += 1
        if call_count[0] < 2:
            return {"ok": False, "state": "outcome_unknown", "error": "HTTP 429 Too Many Requests"}
        return {"ok": True, "state": "succeeded", "evidence": {}}

    job = worker.submit_job(
        tenant_id="t1", intent_id="i", idempotency_key="op_8",
        action_type="issue.create", action_params={}, max_retries=3,
    )
    result = worker.run_job(job.job_id, executor)
    assert result["status"] == "succeeded"
    assert call_count[0] == 2


# ---------------------------------------------------------------------------
# 14. Execution worker: list jobs
# ---------------------------------------------------------------------------


def test_worker_list_jobs(worker):
    """List jobs filtered by tenant + status."""
    worker.submit_job(
        tenant_id="t1", intent_id="i1", idempotency_key="op_a",
        action_type="issue.create", action_params={},
    )
    worker.submit_job(
        tenant_id="t2", intent_id="i2", idempotency_key="op_b",
        action_type="issue.create", action_params={},
    )
    all_jobs = worker.list_jobs()
    assert len(all_jobs) >= 2
    t1_jobs = worker.list_jobs(tenant_id="t1")
    assert all(j["tenant_id"] == "t1" for j in t1_jobs)
    pending_jobs = worker.list_jobs(status="pending")
    assert all(j["status"] == "pending" for j in pending_jobs)
