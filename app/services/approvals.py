from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.metrics import get_metrics_registry
from app.models import (
    ActionIntentRecord,
    ApprovalAssignmentStatus,
    ApprovalDecision,
    ApprovalDecisionType,
    ApprovalRequest,
    ApprovalRequestStatus,
    ApprovalState,
    ApproverAssignment,
    EvidenceObject,
    EvidenceStatus,
)

workflow_logger = logging.getLogger("action_control_plane.workflow")


class ApprovalRequestNotFoundError(LookupError):
    pass


class ApprovalDecisionStateError(RuntimeError):
    pass


class ApprovalAuthorizationError(PermissionError):
    pass


class ApprovalValidationError(ValueError):
    pass


@dataclass(slots=True)
class ApprovalActor:
    principal_type: str
    principal_id: str
    claimed_role_ids: list[str]


@dataclass(slots=True)
class ApprovalDecisionSubmission:
    request: ApprovalRequest
    decision: ApprovalDecision


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ApprovalService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def initialize_for_action_intent(self, record: ActionIntentRecord) -> list[ApprovalRequest]:
        requirement = record.approval_requirement or {}
        if not requirement:
            record.approval_state = ApprovalState.not_required
            return []

        existing_requests = list(
            self.session.scalars(
                self._request_query().where(
                    ApprovalRequest.action_intent_record_id == record.action_intent_record_id
                )
            )
        )
        if existing_requests:
            self.synchronize_action_intent_state(record)
            return existing_requests

        approval_request = ApprovalRequest(
            approval_request_id=uuid4().hex,
            tenant_id=record.tenant_id,
            action_intent_record_id=record.action_intent_record_id,
            policy_id=record.policy_id,
            workflow_rule_id=record.matched_rule_id,
            approval_group_key=(
                requirement.get("approval_group_key")
                or record.matched_rule_id
                or "default"
            ),
            required_decision_count=max(int(requirement.get("required_decision_count", 1)), 1),
            eligible_role_ids=list(requirement.get("eligible_role_ids", [])),
            separation_of_duties={
                "require_requester_separation": requirement.get(
                    "require_requester_separation",
                    True,
                ),
                "require_distinct_approvers": requirement.get(
                    "require_distinct_approvers",
                    True,
                ),
            },
            status=ApprovalRequestStatus.pending,
            expires_at=self._expires_at(
                base_time=record.created_at,
                ttl_seconds=requirement.get("expires_in_seconds"),
            ),
        )
        self.session.add(approval_request)
        self.session.flush()

        for principal_id in requirement.get("eligible_principal_ids", []):
            assignment = ApproverAssignment(
                approval_assignment_id=uuid4().hex,
                approval_request_id=approval_request.approval_request_id,
                tenant_id=record.tenant_id,
                principal_type="user",
                principal_id=principal_id,
                assignment_status=ApprovalAssignmentStatus.assigned,
            )
            self.session.add(assignment)

        self.synchronize_action_intent_state(record)
        return [approval_request]

    def list_requests(
        self,
        *,
        tenant_id: str | None = None,
        action_intent_record_id: str | None = None,
        status: ApprovalRequestStatus | None = None,
    ) -> list[ApprovalRequest]:
        query = self._request_query().order_by(ApprovalRequest.created_at.asc())
        if tenant_id is not None:
            query = query.where(ApprovalRequest.tenant_id == tenant_id)
        if action_intent_record_id is not None:
            query = query.where(ApprovalRequest.action_intent_record_id == action_intent_record_id)
        if status is not None:
            query = query.where(ApprovalRequest.status == status)

        requests = list(self.session.scalars(query))
        changed = False
        for request in requests:
            if self._refresh_request_if_expired(request):
                self.synchronize_action_intent_state(request.action_intent)
                changed = True
        if changed:
            self.session.commit()
            requests = list(self.session.scalars(query))
        return requests

    def get_request(self, approval_request_id: str) -> ApprovalRequest:
        request = self.session.scalar(
            self._request_query().where(ApprovalRequest.approval_request_id == approval_request_id)
        )
        if request is None:
            raise ApprovalRequestNotFoundError(
                f"approval request '{approval_request_id}' was not found"
            )

        if self._refresh_request_if_expired(request):
            self.synchronize_action_intent_state(request.action_intent)
            self.session.commit()
            request = self.session.scalar(
                self._request_query().where(
                    ApprovalRequest.approval_request_id == approval_request_id
                )
            )
            if request is None:
                raise RuntimeError("approval request disappeared during status refresh")
        return request

    def record_decision(
        self,
        approval_request_id: str,
        *,
        actor: ApprovalActor,
        decision: ApprovalDecisionType,
        decision_reason: str | None,
        evidence_object_ids: list[str],
    ) -> ApprovalDecisionSubmission:
        started = perf_counter()
        decision_counter = get_metrics_registry().counter(
            "action_control_plane_approval_decisions_total",
            "Approval decisions recorded by decision and resulting approval status.",
            label_names=("decision", "approval_status"),
        )

        try:
            approval_request = self.get_request(approval_request_id)

            if approval_request.status != ApprovalRequestStatus.pending:
                raise ApprovalDecisionStateError(
                    "approval request is not open for decisions "
                    f"(status={approval_request.status.value})"
                )

            if self._has_existing_decision(approval_request, actor):
                raise ApprovalDecisionStateError(
                    "principal has already decided this approval request"
                )

            self._validate_actor(approval_request, actor)
            self._validate_evidence_references(approval_request, evidence_object_ids)

            approval_decision = ApprovalDecision(
                approval_decision_id=uuid4().hex,
                approval_request=approval_request,
                approval_request_id=approval_request.approval_request_id,
                tenant_id=approval_request.tenant_id,
                decided_by_principal_type=actor.principal_type,
                decided_by_principal_id=actor.principal_id,
                decision=decision,
                decision_reason=decision_reason,
                evidence_object_ids=evidence_object_ids,
            )
            self.session.add(approval_decision)

            for assignment in approval_request.assignments:
                if (
                    assignment.principal_type == actor.principal_type
                    and assignment.principal_id == actor.principal_id
                ):
                    assignment.assignment_status = ApprovalAssignmentStatus.completed
                    assignment.acted_at = utc_now()
                    self.session.add(assignment)

            self.session.flush()
            self._update_request_status_after_decision(approval_request, approval_decision)
            self.synchronize_action_intent_state(approval_request.action_intent)
            self.session.commit()
            refreshed_request = self.get_request(approval_request.approval_request_id)

            duration_ms = int((perf_counter() - started) * 1000)
            decision_counter.inc(
                decision=approval_decision.decision.value,
                approval_status=refreshed_request.status.value,
            )
            workflow_logger.info(
                "approval.decision.recorded",
                extra={
                    "event": "approval.decision.recorded",
                    "tenant_id": refreshed_request.tenant_id,
                    "principal_type": actor.principal_type,
                    "principal_id": actor.principal_id,
                    "action_intent_record_id": refreshed_request.action_intent_record_id,
                    "approval_request_id": refreshed_request.approval_request_id,
                    "decision": approval_decision.decision.value,
                    "approval_state": refreshed_request.action_intent.approval_state.value,
                    "outcome": refreshed_request.status.value,
                    "duration_ms": duration_ms,
                },
            )
            return ApprovalDecisionSubmission(request=refreshed_request, decision=approval_decision)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            log_method = (
                workflow_logger.warning
                if isinstance(
                    exc,
                    (
                        ApprovalDecisionStateError,
                        ApprovalAuthorizationError,
                        ApprovalValidationError,
                    ),
                )
                else workflow_logger.exception
            )
            log_method(
                "approval.decision.failed",
                extra={
                    "event": "approval.decision.failed",
                    "principal_type": actor.principal_type,
                    "principal_id": actor.principal_id,
                    "approval_request_id": approval_request_id,
                    "decision": decision.value,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            raise

    def synchronize_action_intent_state(self, record: ActionIntentRecord) -> ApprovalState:
        requests = list(
            self.session.scalars(
                self._request_query().where(
                    ApprovalRequest.action_intent_record_id == record.action_intent_record_id
                )
            )
        )

        for request in requests:
            self._refresh_request_if_expired(request)

        if not requests:
            record.approval_state = (
                ApprovalState.not_started
                if record.approval_requirement
                else ApprovalState.not_required
            )
            self.session.add(record)
            return record.approval_state

        statuses = {request.status for request in requests}
        if ApprovalRequestStatus.rejected in statuses:
            record.approval_state = ApprovalState.rejected
        elif ApprovalRequestStatus.expired in statuses:
            record.approval_state = ApprovalState.expired
        elif statuses == {ApprovalRequestStatus.satisfied}:
            record.approval_state = ApprovalState.satisfied
        elif statuses == {ApprovalRequestStatus.canceled}:
            record.approval_state = ApprovalState.canceled
        else:
            record.approval_state = ApprovalState.pending

        self.session.add(record)
        return record.approval_state

    def _request_query(self):
        return select(ApprovalRequest).options(
            selectinload(ApprovalRequest.assignments),
            selectinload(ApprovalRequest.decisions),
            selectinload(ApprovalRequest.action_intent),
        )

    def _refresh_request_if_expired(self, approval_request: ApprovalRequest) -> bool:
        if approval_request.status != ApprovalRequestStatus.pending:
            return False
        if approval_request.expires_at is None:
            return False
        if normalize_utc(approval_request.expires_at) > utc_now():
            return False

        approval_request.status = ApprovalRequestStatus.expired
        approval_request.decision_reason = (
            approval_request.decision_reason
            or "approval request expired before the required decision count was reached"
        )
        for assignment in approval_request.assignments:
            if assignment.assignment_status == ApprovalAssignmentStatus.assigned:
                assignment.assignment_status = ApprovalAssignmentStatus.expired
                self.session.add(assignment)
        self.session.add(approval_request)
        return True

    def _validate_actor(self, approval_request: ApprovalRequest, actor: ApprovalActor) -> None:
        if approval_request.assignments and not any(
            assignment.principal_type == actor.principal_type
            and assignment.principal_id == actor.principal_id
            for assignment in approval_request.assignments
        ):
            raise ApprovalAuthorizationError("principal is not assigned to this approval request")

        if approval_request.eligible_role_ids and not (
            set(actor.claimed_role_ids) & set(approval_request.eligible_role_ids)
        ):
            raise ApprovalAuthorizationError(
                "principal does not satisfy any eligible approval role for this request"
            )

        requester_separation = approval_request.separation_of_duties.get(
            "require_requester_separation",
            True,
        )
        if (
            requester_separation
            and approval_request.action_intent.requested_by_principal_type == actor.principal_type
            and approval_request.action_intent.requested_by_principal_id == actor.principal_id
        ):
            raise ApprovalAuthorizationError(
                "requester may not satisfy this approval request"
            )

    def _validate_evidence_references(
        self,
        approval_request: ApprovalRequest,
        evidence_object_ids: list[str],
    ) -> None:
        if not evidence_object_ids:
            return

        evidence_objects = list(
            self.session.scalars(
                select(EvidenceObject).where(
                    EvidenceObject.evidence_object_id.in_(evidence_object_ids)
                )
            )
        )
        if len(evidence_objects) != len(set(evidence_object_ids)):
            raise ApprovalValidationError("all cited evidence objects must exist")

        for evidence_object in evidence_objects:
            if evidence_object.tenant_id != approval_request.tenant_id:
                raise ApprovalValidationError("cited evidence must belong to the same tenant")
            if evidence_object.action_intent_record_id != approval_request.action_intent_record_id:
                raise ApprovalValidationError(
                    "cited evidence must belong to the same Action Intent"
                )
            if evidence_object.status != EvidenceStatus.active:
                raise ApprovalValidationError(
                    "expired or revoked evidence may not satisfy approvals"
                )

    def _has_existing_decision(
        self,
        approval_request: ApprovalRequest,
        actor: ApprovalActor,
    ) -> bool:
        return any(
            decision.decided_by_principal_type == actor.principal_type
            and decision.decided_by_principal_id == actor.principal_id
            for decision in approval_request.decisions
        )

    def _update_request_status_after_decision(
        self,
        approval_request: ApprovalRequest,
        approval_decision: ApprovalDecision,
    ) -> None:
        if approval_decision.decision == ApprovalDecisionType.reject:
            approval_request.status = ApprovalRequestStatus.rejected
            approval_request.rejected_at = approval_decision.created_at
            approval_request.decision_reason = (
                approval_decision.decision_reason or "approval request rejected"
            )
            self.session.add(approval_request)
            return

        approve_count = sum(
            1
            for decision in approval_request.decisions
            if decision.decision == ApprovalDecisionType.approve
        )
        if approve_count >= approval_request.required_decision_count:
            approval_request.status = ApprovalRequestStatus.satisfied
            approval_request.satisfied_at = approval_decision.created_at
            approval_request.decision_reason = (
                approval_decision.decision_reason
                or "required approval decision count satisfied"
            )
        else:
            approval_request.status = ApprovalRequestStatus.pending
        self.session.add(approval_request)

    def _expires_at(self, *, base_time: datetime, ttl_seconds: Any) -> datetime | None:
        if ttl_seconds in (None, "", 0):
            return None
        return normalize_utc(base_time) + timedelta(seconds=int(ttl_seconds))
