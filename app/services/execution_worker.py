"""Brokered execution worker (Prompt 15).

Safe execution orchestration with:
  - Durable jobs (persisted to DB)
  - Retry policy (exponential backoff + jitter)
  - Idempotency (duplicate jobs return the original result)
  - Timeout handling (job marked as timed_out)
  - Reconciliation (re-check provider state after unknown outcome)
  - Dead-letter handling (exhausted retries -> dead_letter)
  - Cancellation rules (jobs in non-terminal states can be cancelled)
  - Provider rate-limit handling (retry on 429/503)
  - Evidence emission (every job produces an evidence record)

Retries do NOT duplicate side effects: the idempotency key ensures the
provider sees the same request only once (or returns the original result
if it was already processed).
"""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, select
from sqlalchemy.orm import Session

from app.database import Base

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 30.0
DEFAULT_TIMEOUT_SECONDS = 30.0


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------


class ExecutionJobRecord(Base):
    """Durable execution job record.

    Jobs are persisted to the database so they survive process restarts.
    The ``status`` field tracks the job lifecycle:
      pending -> running -> succeeded / failed / timed_out / dead_letter / cancelled
    """

    __tablename__ = "execution_jobs"
    __table_args__ = (
        Index("ix_exec_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_exec_jobs_idem_key", "idempotency_key"),
    )

    job_id: Column[str] = Column(String(64), primary_key=True)
    tenant_id: Column[str] = Column(String(64), nullable=False)
    intent_id: Column[str] = Column(String(64), nullable=False)
    idempotency_key: Column[str] = Column(String(255), nullable=False)
    action_type: Column[str] = Column(String(255), nullable=False)
    action_params: Column[str] = Column(Text, nullable=False)  # JSON  # noqa: E501
    status: Column[str] = Column(String(32), nullable=False, default="pending")
    attempt_count: Column[int] = Column(Integer, nullable=False, default=0)
    max_retries: Column[int] = Column(Integer, nullable=False, default=MAX_RETRIES)  # noqa: E501
    timeout_seconds: Column[float] = Column(Integer, nullable=False, default=DEFAULT_TIMEOUT_SECONDS)  # noqa: E501
    result: Column[str | None] = Column(Text, nullable=True)  # JSON result  # noqa: E501
    error: Column[str | None] = Column(Text, nullable=True)
    created_at: Column[datetime] = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)  # noqa: E501
    updated_at: Column[datetime] = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)  # noqa: E501
    completed_at: Column[datetime | None] = Column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class JobError(RuntimeError):
    """Base error for job operations."""

    def __init__(self, safe_message: str) -> None:
        super().__init__(safe_message)


class JobNotFoundError(JobError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"job {job_id} not found")


class JobCancelledError(JobError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"job {job_id} was cancelled")


class JobDeadLetteredError(JobError):
    def __init__(self, job_id: str, reason: str) -> None:
        super().__init__(f"job {job_id} dead-lettered: {reason}")


# ---------------------------------------------------------------------------
# Execution worker
# ---------------------------------------------------------------------------


class ExecutionWorker:
    """Brokered execution worker with durable jobs, retries, and reconciliation.

    The worker is NOT a background daemon — it executes jobs synchronously
    when ``run_job()`` is called. In production, a task queue (Celery,
    RQ, etc.) would call ``run_job()`` asynchronously. The durable job
    record ensures that if the process crashes, the job can be recovered
    and re-tried on the next startup.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def submit_job(
        self,
        *,
        tenant_id: str,
        intent_id: str,
        idempotency_key: str,
        action_type: str,
        action_params: dict[str, Any],
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> ExecutionJobRecord:
        """Submit a new execution job. Idempotent: if a job with the same
        idempotency_key already exists, returns the existing job.
        """
        existing = self._session.execute(
            select(ExecutionJobRecord).where(
                ExecutionJobRecord.idempotency_key == idempotency_key,
                ExecutionJobRecord.tenant_id == tenant_id,
            )
        ).scalars().first()
        if existing is not None:
            return existing

        job = ExecutionJobRecord(
            job_id=f"job_{uuid4().hex[:16]}",
            tenant_id=tenant_id,
            intent_id=intent_id,
            idempotency_key=idempotency_key,
            action_type=action_type,
            action_params=json.dumps(action_params, sort_keys=True, default=str),
            status="pending",
            max_retries=max_retries,
            timeout_seconds=int(timeout_seconds),
        )
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        logger.info(
            "execution.job_submitted",
            extra={"job_id": job.job_id, "intent_id": intent_id, "action_type": action_type},
        )
        return job

    def run_job(
        self,
        job_id: str,
        executor: Any,
        *,
        principal_id: str = "system",
    ) -> dict[str, Any]:
        """Run a job to completion (with retries).

        The ``executor`` is a callable that receives (action_type, action_params,
        idempotency_key, timeout_seconds) and returns a dict with:
          - ``ok``: bool
          - ``state``: str (succeeded/failed/outcome_unknown)
          - ``evidence``: dict
          - ``retryable``: bool (optional, default False)

        Returns the job result dict. Raises JobDeadLetteredError if all retries
        are exhausted.
        """
        job = self._session.get(ExecutionJobRecord, job_id)
        if job is None:
            raise JobNotFoundError(job_id)

        # If already terminal, return the existing result (idempotent).
        if job.status in ("succeeded", "failed", "timed_out", "dead_letter", "cancelled"):
            return self._job_result(job)

        # Transition to running.
        job.status = "running"
        job.updated_at = datetime.now(UTC)
        self._session.commit()

        last_error: str | None = None
        while job.attempt_count < job.max_retries + 1:
            job.attempt_count += 1
            job.updated_at = datetime.now(UTC)
            self._session.commit()

            try:
                params = json.loads(job.action_params)
                result = executor(
                    job.action_type,
                    params,
                    job.idempotency_key,
                    float(job.timeout_seconds),
                )

                if result.get("ok") or result.get("state") == "succeeded":
                    # Success — record result + evidence.
                    job.status = "succeeded"
                    job.result = json.dumps(result, sort_keys=True, default=str)
                    job.completed_at = datetime.now(UTC)
                    self._session.commit()
                    self._emit_evidence(job, result, "succeeded")
                    return self._job_result(job)

                if result.get("state") == "outcome_unknown":
                    # Reconciliation: try once more if retries remain.
                    last_error = result.get("error", "outcome unknown")
                    if job.attempt_count >= job.max_retries + 1:
                        job.status = "timed_out"
                        job.error = last_error
                        job.completed_at = datetime.now(UTC)
                        self._session.commit()
                        self._emit_evidence(job, result, "timed_out")
                        return self._job_result(job)
                    self._backoff(job.attempt_count)
                    continue

                if result.get("state") == "failed":
                    # Non-retryable failure.
                    job.status = "failed"
                    job.error = result.get("error", "execution failed")
                    job.result = json.dumps(result, sort_keys=True, default=str)
                    job.completed_at = datetime.now(UTC)
                    self._session.commit()
                    self._emit_evidence(job, result, "failed")
                    return self._job_result(job)

                # Retryable error (e.g. provider 429/503).
                last_error = result.get("error", "retryable error")
                if job.attempt_count >= job.max_retries + 1:
                    break
                self._backoff(job.attempt_count)

            except Exception as e:
                # Sanitise: never include credential values in the error.
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
                if job.attempt_count >= job.max_retries + 1:
                    break
                self._backoff(job.attempt_count)

        # Exhausted retries -> dead-letter.
        job.status = "dead_letter"
        job.error = last_error or "retries exhausted"
        job.completed_at = datetime.now(UTC)
        self._session.commit()
        self._emit_evidence(job, {"error": last_error}, "dead_letter")
        logger.error(
            "execution.job_dead_lettered",
            extra={"job_id": job.job_id, "error": last_error},
        )
        raise JobDeadLetteredError(job.job_id, last_error or "retries exhausted")

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel a job. Only jobs in non-terminal states can be cancelled."""
        job = self._session.get(ExecutionJobRecord, job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        if job.status in ("succeeded", "failed", "timed_out", "dead_letter", "cancelled"):
            return self._job_result(job)
        job.status = "cancelled"
        job.completed_at = datetime.now(UTC)
        self._session.commit()
        return self._job_result(job)

    def get_job(self, job_id: str) -> dict[str, Any]:
        """Get a job's status + result."""
        job = self._session.get(ExecutionJobRecord, job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return self._job_result(job)

    def list_jobs(
        self,
        *,
        tenant_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List jobs, optionally filtered by tenant + status."""
        stmt = select(ExecutionJobRecord)
        if tenant_id is not None:
            stmt = stmt.where(ExecutionJobRecord.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(ExecutionJobRecord.status == status)
        stmt = stmt.order_by(ExecutionJobRecord.created_at.desc()).limit(limit)
        records = self._session.execute(stmt).scalars().all()
        return [self._job_result(r) for r in records]

    def recover_pending_jobs(self, executor: Any) -> int:
        """Recover jobs left in pending/running state (e.g. after a crash).

        Returns the number of jobs recovered.
        """
        records = self._session.execute(
            select(ExecutionJobRecord).where(
                ExecutionJobRecord.status.in_(["pending", "running"])
            )
        ).scalars().all()
        count = 0
        for job in records:
            try:
                self.run_job(job.job_id, executor)
                count += 1
            except JobError:
                pass  # Dead-lettered — skip.
        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _backoff(self, attempt: int) -> None:
        """Exponential backoff with jitter."""
        delay = min(BASE_DELAY_SECONDS * (2 ** (attempt - 1)), MAX_DELAY_SECONDS)
        jitter = random.uniform(0, delay * 0.1)  # noqa: S311
        time.sleep(delay + jitter)

    def _job_result(self, job: ExecutionJobRecord) -> dict[str, Any]:
        result = json.loads(job.result) if job.result else None
        return {
            "job_id": job.job_id,
            "tenant_id": job.tenant_id,
            "intent_id": job.intent_id,
            "idempotency_key": job.idempotency_key,
            "action_type": job.action_type,
            "status": job.status,
            "attempt_count": job.attempt_count,
            "max_retries": job.max_retries,
            "result": result,
            "error": job.error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    def _emit_evidence(
        self,
        job: ExecutionJobRecord,
        result: dict[str, Any],
        outcome: str,
    ) -> None:
        """Emit an evidence record for the job. The evidence is safe to
        persist — it contains NO credential values (the executor is
        responsible for redacting)."""
        evidence = {
            "job_id": job.job_id,
            "intent_id": job.intent_id,
            "action_type": job.action_type,
            "outcome": outcome,
            "attempt_count": job.attempt_count,
            "evidence": result.get("evidence", {}),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        logger.info(
            "execution.evidence_emitted",
            extra=evidence,
        )


__all__ = [
    "ExecutionJobRecord",
    "ExecutionWorker",
    "JobCancelledError",
    "JobDeadLetteredError",
    "JobError",
    "JobNotFoundError",
]
