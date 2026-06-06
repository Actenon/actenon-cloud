from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.metrics import get_metrics_registry
from app.models import (
    ActionIntentRecord,
    ApprovalRequest,
    EvidenceObject,
    EvidenceState,
    EvidenceStatus,
    EvidenceStorageMode,
    EvidenceType,
)
from app.services.evidence_backends import (
    EvidenceBackend,
    EvidenceBackendError,
    EvidenceBackendNotReadyError,
    FilesystemEvidenceBackend,
    ObjectStoreEvidenceBackend,
)

workflow_logger = logging.getLogger("action_control_plane.workflow")


class EvidenceObjectNotFoundError(LookupError):
    pass


class EvidenceValidationError(ValueError):
    pass


class EvidenceContentUnavailableError(RuntimeError):
    pass


class EvidenceBackendUnavailableError(RuntimeError):
    pass


@dataclass(slots=True)
class EvidencePrincipal:
    principal_type: str
    principal_id: str


@dataclass(slots=True)
class EvidenceContent:
    evidence_object: EvidenceObject
    path: Path


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class EvidenceService:
    def __init__(
        self,
        session: Session,
        *,
        upload_backend: EvidenceBackend,
        content_backends: dict[EvidenceStorageMode, EvidenceBackend] | None = None,
    ) -> None:
        self.session = session
        self.upload_backend = upload_backend
        self.content_backends = dict(content_backends or {})
        self.content_backends.setdefault(upload_backend.storage_mode, upload_backend)

    @classmethod
    def from_settings(cls, session: Session, *, settings: Settings) -> EvidenceService:
        filesystem_backend = FilesystemEvidenceBackend(settings.evidence_storage_root)
        content_backends: dict[EvidenceStorageMode, EvidenceBackend] = {
            EvidenceStorageMode.filesystem: filesystem_backend,
        }

        object_store_backend: EvidenceBackend | None = None
        if settings.evidence_object_store_bucket is not None:
            object_store_backend = ObjectStoreEvidenceBackend(
                bucket=settings.evidence_object_store_bucket,
                prefix=settings.evidence_object_store_prefix,
                endpoint=settings.evidence_object_store_endpoint,
            )
            content_backends[EvidenceStorageMode.object_store] = object_store_backend

        if settings.evidence_upload_backend == "filesystem":
            upload_backend = filesystem_backend
        else:
            if object_store_backend is None:
                raise ValueError(
                    "object_store evidence upload backend requires evidence_object_store_bucket"
                )
            upload_backend = object_store_backend

        return cls(
            session,
            upload_backend=upload_backend,
            content_backends=content_backends,
        )

    def initialize_for_action_intent(self, record: ActionIntentRecord) -> EvidenceState:
        if not record.evidence_requirement:
            record.evidence_state = EvidenceState.not_required
            self.session.add(record)
            return record.evidence_state

        record.evidence_state = EvidenceState.pending
        self.session.add(record)
        return record.evidence_state

    def list_evidence(
        self,
        *,
        tenant_id: str | None = None,
        action_intent_record_id: str | None = None,
        approval_request_id: str | None = None,
    ) -> list[EvidenceObject]:
        query = select(EvidenceObject).order_by(EvidenceObject.created_at.asc())
        if tenant_id is not None:
            query = query.where(EvidenceObject.tenant_id == tenant_id)
        if action_intent_record_id is not None:
            query = query.where(EvidenceObject.action_intent_record_id == action_intent_record_id)
        if approval_request_id is not None:
            query = query.where(EvidenceObject.approval_request_id == approval_request_id)

        evidence_objects = list(self.session.scalars(query))
        changed = False
        for evidence_object in evidence_objects:
            if self._refresh_if_expired(evidence_object):
                action_intent = self.session.get(
                    ActionIntentRecord,
                    evidence_object.action_intent_record_id,
                )
                if action_intent is None:
                    raise RuntimeError("linked Action Intent disappeared during evidence refresh")
                self.synchronize_action_intent_state(action_intent)
                changed = True
        if changed:
            self.session.commit()
            evidence_objects = list(self.session.scalars(query))
        return evidence_objects

    def get_evidence(self, evidence_object_id: str) -> EvidenceObject:
        evidence_object = self.session.get(EvidenceObject, evidence_object_id)
        if evidence_object is None:
            raise EvidenceObjectNotFoundError(
                f"evidence object '{evidence_object_id}' was not found"
            )

        if self._refresh_if_expired(evidence_object):
            action_intent = self.session.get(
                ActionIntentRecord,
                evidence_object.action_intent_record_id,
            )
            if action_intent is None:
                raise RuntimeError("linked Action Intent disappeared during evidence refresh")
            self.synchronize_action_intent_state(action_intent)
            self.session.commit()
            evidence_object = self.session.get(EvidenceObject, evidence_object_id)
            if evidence_object is None:
                raise RuntimeError("evidence object disappeared during status refresh")
        return evidence_object

    def get_evidence_content(self, evidence_object_id: str) -> EvidenceContent:
        evidence_object = self.get_evidence(evidence_object_id)
        backend = self.content_backends.get(evidence_object.storage_mode)
        if backend is None:
            raise EvidenceContentUnavailableError(
                self._content_unavailable_message(evidence_object.storage_mode)
            )

        try:
            content_path = backend.open_content(evidence_object)
        except FileNotFoundError as exc:
            raise EvidenceObjectNotFoundError(str(exc)) from exc
        except (EvidenceBackendError, ValueError) as exc:
            raise EvidenceContentUnavailableError(str(exc)) from exc

        return EvidenceContent(evidence_object=evidence_object, path=content_path)

    def register_evidence(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        approval_request_id: str | None,
        evidence_type: EvidenceType,
        storage_mode: EvidenceStorageMode,
        storage_ref: str,
        original_filename: str | None,
        media_type: str | None,
        content_digest: str | None,
        size_bytes: int | None,
        uploaded_by: EvidencePrincipal,
        evidence_metadata: dict[str, Any],
        expires_at: datetime | None,
    ) -> EvidenceObject:
        started = perf_counter()
        evidence_counter = get_metrics_registry().counter(
            "action_control_plane_evidence_mutations_total",
            "Evidence mutations by operation, evidence type, storage mode, and status.",
            label_names=("operation", "evidence_type", "storage_mode", "status"),
        )

        try:
            action_intent = self._get_action_intent(tenant_id, action_intent_record_id)
            self._validate_approval_binding(action_intent, approval_request_id)

            evidence_object = EvidenceObject(
                evidence_object_id=uuid4().hex,
                tenant_id=tenant_id,
                action_intent_record_id=action_intent_record_id,
                approval_request_id=approval_request_id,
                evidence_type=evidence_type,
                storage_mode=storage_mode,
                storage_ref=storage_ref,
                original_filename=original_filename,
                media_type=media_type,
                content_digest=content_digest,
                size_bytes=size_bytes,
                uploaded_by_principal_type=uploaded_by.principal_type,
                uploaded_by_principal_id=uploaded_by.principal_id,
                evidence_metadata=evidence_metadata,
                expires_at=self._resolve_expiration(action_intent, expires_at),
                status=EvidenceStatus.active,
            )
            self.session.add(evidence_object)
            self.session.flush()
            self._refresh_if_expired(evidence_object)
            self.synchronize_action_intent_state(action_intent)
            self.session.commit()
            self.session.refresh(evidence_object)

            duration_ms = int((perf_counter() - started) * 1000)
            evidence_counter.inc(
                operation="register",
                evidence_type=evidence_object.evidence_type.value,
                storage_mode=evidence_object.storage_mode.value,
                status=evidence_object.status.value,
            )
            workflow_logger.info(
                "evidence.registered",
                extra={
                    "event": "evidence.registered",
                    "tenant_id": evidence_object.tenant_id,
                    "principal_type": evidence_object.uploaded_by_principal_type,
                    "principal_id": evidence_object.uploaded_by_principal_id,
                    "action_intent_record_id": evidence_object.action_intent_record_id,
                    "approval_request_id": evidence_object.approval_request_id,
                    "evidence_object_id": evidence_object.evidence_object_id,
                    "evidence_type": evidence_object.evidence_type.value,
                    "storage_mode": evidence_object.storage_mode.value,
                    "evidence_state": action_intent.evidence_state.value,
                    "outcome": evidence_object.status.value,
                    "duration_ms": duration_ms,
                },
            )
            return evidence_object
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            log_method = (
                workflow_logger.warning
                if isinstance(exc, EvidenceValidationError)
                else workflow_logger.exception
            )
            log_method(
                "evidence.register.failed",
                extra={
                    "event": "evidence.register.failed",
                    "tenant_id": tenant_id,
                    "principal_type": uploaded_by.principal_type,
                    "principal_id": uploaded_by.principal_id,
                    "action_intent_record_id": action_intent_record_id,
                    "approval_request_id": approval_request_id,
                    "evidence_type": evidence_type.value,
                    "storage_mode": storage_mode.value,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            raise

    def upload_evidence(
        self,
        *,
        tenant_id: str,
        action_intent_record_id: str,
        approval_request_id: str | None,
        evidence_type: EvidenceType,
        uploaded_by: EvidencePrincipal,
        original_filename: str,
        media_type: str | None,
        evidence_metadata: dict[str, Any],
        expires_at: datetime | None,
        payload: bytes,
    ) -> EvidenceObject:
        started = perf_counter()
        evidence_counter = get_metrics_registry().counter(
            "action_control_plane_evidence_mutations_total",
            "Evidence mutations by operation, evidence type, storage mode, and status.",
            label_names=("operation", "evidence_type", "storage_mode", "status"),
        )

        try:
            action_intent = self._get_action_intent(tenant_id, action_intent_record_id)
            self._validate_approval_binding(action_intent, approval_request_id)

            evidence_object_id = uuid4().hex
            try:
                stored_artifact = self.upload_backend.store_upload(
                    tenant_id=tenant_id,
                    action_intent_record_id=action_intent_record_id,
                    evidence_object_id=evidence_object_id,
                    filename=original_filename,
                    payload=payload,
                )
            except EvidenceBackendNotReadyError as exc:
                raise EvidenceBackendUnavailableError(str(exc)) from exc
            evidence_object = EvidenceObject(
                evidence_object_id=evidence_object_id,
                tenant_id=tenant_id,
                action_intent_record_id=action_intent_record_id,
                approval_request_id=approval_request_id,
                evidence_type=evidence_type,
                storage_mode=stored_artifact.storage_mode,
                storage_ref=stored_artifact.storage_ref,
                original_filename=original_filename,
                media_type=media_type,
                content_digest=stored_artifact.content_digest,
                size_bytes=stored_artifact.size_bytes,
                uploaded_by_principal_type=uploaded_by.principal_type,
                uploaded_by_principal_id=uploaded_by.principal_id,
                evidence_metadata=evidence_metadata,
                expires_at=self._resolve_expiration(action_intent, expires_at),
                status=EvidenceStatus.active,
            )
            self.session.add(evidence_object)
            self.session.flush()
            self._refresh_if_expired(evidence_object)
            self.synchronize_action_intent_state(action_intent)
            self.session.commit()
            self.session.refresh(evidence_object)

            duration_ms = int((perf_counter() - started) * 1000)
            evidence_counter.inc(
                operation="upload",
                evidence_type=evidence_object.evidence_type.value,
                storage_mode=evidence_object.storage_mode.value,
                status=evidence_object.status.value,
            )
            workflow_logger.info(
                "evidence.uploaded",
                extra={
                    "event": "evidence.uploaded",
                    "tenant_id": evidence_object.tenant_id,
                    "principal_type": evidence_object.uploaded_by_principal_type,
                    "principal_id": evidence_object.uploaded_by_principal_id,
                    "action_intent_record_id": evidence_object.action_intent_record_id,
                    "approval_request_id": evidence_object.approval_request_id,
                    "evidence_object_id": evidence_object.evidence_object_id,
                    "evidence_type": evidence_object.evidence_type.value,
                    "storage_mode": evidence_object.storage_mode.value,
                    "evidence_state": action_intent.evidence_state.value,
                    "outcome": evidence_object.status.value,
                    "duration_ms": duration_ms,
                },
            )
            return evidence_object
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            log_method = (
                workflow_logger.warning
                if isinstance(
                    exc,
                    (
                        EvidenceValidationError,
                        EvidenceBackendUnavailableError,
                    ),
                )
                else workflow_logger.exception
            )
            log_method(
                "evidence.upload.failed",
                extra={
                    "event": "evidence.upload.failed",
                    "tenant_id": tenant_id,
                    "principal_type": uploaded_by.principal_type,
                    "principal_id": uploaded_by.principal_id,
                    "action_intent_record_id": action_intent_record_id,
                    "approval_request_id": approval_request_id,
                    "evidence_type": evidence_type.value,
                    "storage_mode": self.upload_backend.storage_mode.value,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            raise

    def synchronize_action_intent_state(self, record: ActionIntentRecord) -> EvidenceState:
        evidence_objects = list(
            self.session.scalars(
                select(EvidenceObject).where(
                    EvidenceObject.action_intent_record_id == record.action_intent_record_id
                )
            )
        )
        for evidence_object in evidence_objects:
            self._refresh_if_expired(evidence_object)

        requirement = record.evidence_requirement or {}
        minimum_count = max(int(requirement.get("minimum_count", 1)), 1) if requirement else 0
        allowed_types = {
            str(evidence_type) for evidence_type in requirement.get("allowed_evidence_types", [])
        }

        if not requirement:
            record.evidence_state = EvidenceState.not_required
        else:
            valid_evidence = [
                evidence_object
                for evidence_object in evidence_objects
                if evidence_object.status == EvidenceStatus.active
                and (
                    not allowed_types
                    or evidence_object.evidence_type.value in allowed_types
                )
            ]
            if len(valid_evidence) >= minimum_count:
                record.evidence_state = EvidenceState.satisfied
            elif any(
                evidence_object.status == EvidenceStatus.expired
                for evidence_object in evidence_objects
            ):
                record.evidence_state = EvidenceState.expired
            else:
                record.evidence_state = EvidenceState.pending

        self.session.add(record)
        return record.evidence_state

    def _get_action_intent(
        self,
        tenant_id: str,
        action_intent_record_id: str,
    ) -> ActionIntentRecord:
        action_intent = self.session.get(ActionIntentRecord, action_intent_record_id)
        if action_intent is None:
            raise EvidenceValidationError(
                f"action intent record '{action_intent_record_id}' was not found"
            )
        if action_intent.tenant_id != tenant_id:
            raise EvidenceValidationError("action intent does not belong to the requested tenant")
        return action_intent

    def _validate_approval_binding(
        self,
        action_intent: ActionIntentRecord,
        approval_request_id: str | None,
    ) -> None:
        if approval_request_id is None:
            return

        approval_request = self.session.get(ApprovalRequest, approval_request_id)
        if approval_request is None:
            raise EvidenceValidationError(
                f"approval request '{approval_request_id}' was not found"
            )
        if approval_request.tenant_id != action_intent.tenant_id:
            raise EvidenceValidationError("approval request belongs to a different tenant")
        if approval_request.action_intent_record_id != action_intent.action_intent_record_id:
            raise EvidenceValidationError("approval request belongs to a different Action Intent")

    def _refresh_if_expired(self, evidence_object: EvidenceObject) -> bool:
        if evidence_object.status != EvidenceStatus.active:
            return False
        if evidence_object.expires_at is None:
            return False
        if normalize_utc(evidence_object.expires_at) > utc_now():
            return False

        evidence_object.status = EvidenceStatus.expired
        self.session.add(evidence_object)
        return True

    def _resolve_expiration(
        self,
        action_intent: ActionIntentRecord,
        explicit_expires_at: datetime | None,
    ) -> datetime | None:
        if explicit_expires_at is not None:
            return normalize_utc(explicit_expires_at)

        requirement = action_intent.evidence_requirement or {}
        ttl_seconds = requirement.get("expires_in_seconds")
        if ttl_seconds in (None, "", 0):
            return None
        return utc_now() + timedelta(seconds=int(ttl_seconds))

    def _content_unavailable_message(self, storage_mode: EvidenceStorageMode) -> str:
        if storage_mode == EvidenceStorageMode.external_uri:
            return "evidence content download is not proxied for external URI evidence"
        if storage_mode == EvidenceStorageMode.inline_metadata_only:
            return "evidence content download is not available for metadata-only evidence"
        if storage_mode == EvidenceStorageMode.object_store:
            return "object-store evidence content retrieval is not configured for this deployment"
        if storage_mode == EvidenceStorageMode.filesystem:
            return "filesystem evidence content retrieval is not configured for this deployment"
        return (
            "evidence content download is not configured for "
            f"storage mode '{storage_mode.value}'"
        )
