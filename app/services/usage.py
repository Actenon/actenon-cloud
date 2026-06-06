from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ActionIntentRecord,
    ApprovalDecision,
    ApprovalRequest,
    DecisionState,
    EvidenceObject,
    IssuedProof,
    ProofIssuanceStatus,
    ReceiptRecord,
)


class UsageReportingValidationError(ValueError):
    pass


@dataclass(slots=True)
class UsageSummaryTotals:
    submitted_actions: int = 0
    billable_proved_and_allowed_actions: int = 0
    blocked_or_refused_actions: int = 0
    blocked_policy_actions: int = 0
    structurally_refused_actions: int = 0
    held_for_review_actions: int = 0
    reviewed_actions: int = 0
    receipt_linked_actions: int = 0


@dataclass(slots=True)
class UsageDailyBucket:
    usage_date: date
    submitted_actions: int = 0
    billable_proved_and_allowed_actions: int = 0
    blocked_or_refused_actions: int = 0
    held_for_review_actions: int = 0
    reviewed_actions: int = 0
    receipt_linked_actions: int = 0


@dataclass(slots=True)
class UsageDefinitions:
    pricing_status: str
    billable_action_definition: str
    blocked_action_definition: str
    reviewed_action_definition: str
    receipt_linked_definition: str


@dataclass(slots=True)
class TenantUsageReport:
    generated_at: datetime
    tenant_id: str
    workflow_key: str | None
    period_start: datetime
    period_end: datetime
    totals: UsageSummaryTotals
    daily_buckets: list[UsageDailyBucket] = field(default_factory=list)
    definitions: UsageDefinitions | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class UsageService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_usage_report(
        self,
        *,
        tenant_id: str,
        workflow_key: str | None = "payments.standard",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> TenantUsageReport:
        start_at, end_at = self._resolve_period(period_start=period_start, period_end=period_end)
        totals = UsageSummaryTotals()
        buckets_by_date: dict[date, UsageDailyBucket] = {}

        self._populate_action_totals(
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            period_start=start_at,
            period_end=end_at,
            totals=totals,
            buckets_by_date=buckets_by_date,
        )
        self._populate_billable_totals(
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            period_start=start_at,
            period_end=end_at,
            totals=totals,
            buckets_by_date=buckets_by_date,
        )
        self._populate_reviewed_totals(
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            period_start=start_at,
            period_end=end_at,
            totals=totals,
            buckets_by_date=buckets_by_date,
        )
        self._populate_receipt_totals(
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            period_start=start_at,
            period_end=end_at,
            totals=totals,
            buckets_by_date=buckets_by_date,
        )

        return TenantUsageReport(
            generated_at=utc_now(),
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            period_start=start_at,
            period_end=end_at,
            totals=totals,
            daily_buckets=[buckets_by_date[key] for key in sorted(buckets_by_date)],
            definitions=UsageDefinitions(
                pricing_status="metering_only_no_invoicing",
                billable_action_definition=(
                    "Distinct Action Intents with a first successful proof issuance in the "
                    "reporting period. This is the current future usage-pricing candidate, "
                    "not a live invoice."
                ),
                blocked_action_definition=(
                    "Distinct Action Intents created in the reporting period with a final "
                    "intake result of deny or structurally_non_executable. These counts show "
                    "prevention value and are not usage-billed."
                ),
                reviewed_action_definition=(
                    "Distinct Action Intents with a first approval decision or evidence "
                    "submission in the reporting period."
                ),
                receipt_linked_definition=(
                    "Distinct Action Intents with a first linked receipt record in the "
                    "reporting period."
                ),
            ),
        )

    def _populate_action_totals(
        self,
        *,
        tenant_id: str,
        workflow_key: str | None,
        period_start: datetime,
        period_end: datetime,
        totals: UsageSummaryTotals,
        buckets_by_date: dict[date, UsageDailyBucket],
    ) -> None:
        query = (
            select(
                ActionIntentRecord.action_intent_record_id,
                ActionIntentRecord.decision_state,
                ActionIntentRecord.created_at,
            )
            .where(
                ActionIntentRecord.tenant_id == tenant_id,
                ActionIntentRecord.created_at >= period_start,
                ActionIntentRecord.created_at < period_end,
            )
            .order_by(ActionIntentRecord.created_at.asc())
        )
        if workflow_key is not None:
            query = query.where(ActionIntentRecord.workflow_key == workflow_key)

        for action_intent_record_id, decision_state, created_at in self.session.execute(query):
            del action_intent_record_id  # counted once per created row
            created_at_utc = normalize_utc(created_at)
            bucket = self._bucket_for(buckets_by_date, created_at_utc.date())
            totals.submitted_actions += 1
            bucket.submitted_actions += 1

            if decision_state == DecisionState.deny:
                totals.blocked_or_refused_actions += 1
                totals.blocked_policy_actions += 1
                bucket.blocked_or_refused_actions += 1
            elif decision_state == DecisionState.structurally_non_executable:
                totals.blocked_or_refused_actions += 1
                totals.structurally_refused_actions += 1
                bucket.blocked_or_refused_actions += 1
            elif decision_state in {
                DecisionState.approval_required,
                DecisionState.needs_evidence,
            }:
                totals.held_for_review_actions += 1
                bucket.held_for_review_actions += 1

    def _populate_billable_totals(
        self,
        *,
        tenant_id: str,
        workflow_key: str | None,
        period_start: datetime,
        period_end: datetime,
        totals: UsageSummaryTotals,
        buckets_by_date: dict[date, UsageDailyBucket],
    ) -> None:
        metered_at = func.coalesce(IssuedProof.issued_at, IssuedProof.created_at).label(
            "metered_at"
        )
        query = (
            select(
                IssuedProof.action_intent_record_id,
                metered_at,
            )
            .join(
                ActionIntentRecord,
                ActionIntentRecord.action_intent_record_id == IssuedProof.action_intent_record_id,
            )
            .where(
                IssuedProof.tenant_id == tenant_id,
                IssuedProof.status == ProofIssuanceStatus.issued,
                metered_at >= period_start,
                metered_at < period_end,
                ActionIntentRecord.decision_state.notin_(
                    [DecisionState.deny, DecisionState.structurally_non_executable]
                ),
            )
            .order_by(IssuedProof.action_intent_record_id.asc(), metered_at.asc())
        )
        if workflow_key is not None:
            query = query.where(ActionIntentRecord.workflow_key == workflow_key)

        first_metered_at_by_action: dict[str, datetime] = {}
        for action_intent_record_id, event_time in self.session.execute(query):
            event_time_utc = normalize_utc(event_time)
            existing = first_metered_at_by_action.get(action_intent_record_id)
            if existing is None or event_time_utc < existing:
                first_metered_at_by_action[action_intent_record_id] = event_time_utc

        for event_time_utc in first_metered_at_by_action.values():
            bucket = self._bucket_for(buckets_by_date, event_time_utc.date())
            totals.billable_proved_and_allowed_actions += 1
            bucket.billable_proved_and_allowed_actions += 1

    def _populate_reviewed_totals(
        self,
        *,
        tenant_id: str,
        workflow_key: str | None,
        period_start: datetime,
        period_end: datetime,
        totals: UsageSummaryTotals,
        buckets_by_date: dict[date, UsageDailyBucket],
    ) -> None:
        first_reviewed_at_by_action: dict[str, datetime] = {}

        approval_query = (
            select(
                ApprovalRequest.action_intent_record_id,
                ApprovalDecision.created_at,
            )
            .join(
                ApprovalRequest,
                ApprovalRequest.approval_request_id == ApprovalDecision.approval_request_id,
            )
            .join(
                ActionIntentRecord,
                ActionIntentRecord.action_intent_record_id
                == ApprovalRequest.action_intent_record_id,
            )
            .where(
                ApprovalDecision.tenant_id == tenant_id,
                ApprovalDecision.created_at >= period_start,
                ApprovalDecision.created_at < period_end,
            )
            .order_by(
                ApprovalRequest.action_intent_record_id.asc(), ApprovalDecision.created_at.asc()
            )
        )
        if workflow_key is not None:
            approval_query = approval_query.where(ActionIntentRecord.workflow_key == workflow_key)

        evidence_query = (
            select(
                EvidenceObject.action_intent_record_id,
                EvidenceObject.created_at,
            )
            .join(
                ActionIntentRecord,
                ActionIntentRecord.action_intent_record_id
                == EvidenceObject.action_intent_record_id,
            )
            .where(
                EvidenceObject.tenant_id == tenant_id,
                EvidenceObject.created_at >= period_start,
                EvidenceObject.created_at < period_end,
            )
            .order_by(EvidenceObject.action_intent_record_id.asc(), EvidenceObject.created_at.asc())
        )
        if workflow_key is not None:
            evidence_query = evidence_query.where(ActionIntentRecord.workflow_key == workflow_key)

        for query in (approval_query, evidence_query):
            for action_intent_record_id, event_time in self.session.execute(query):
                event_time_utc = normalize_utc(event_time)
                existing = first_reviewed_at_by_action.get(action_intent_record_id)
                if existing is None or event_time_utc < existing:
                    first_reviewed_at_by_action[action_intent_record_id] = event_time_utc

        for event_time_utc in first_reviewed_at_by_action.values():
            bucket = self._bucket_for(buckets_by_date, event_time_utc.date())
            totals.reviewed_actions += 1
            bucket.reviewed_actions += 1

    def _populate_receipt_totals(
        self,
        *,
        tenant_id: str,
        workflow_key: str | None,
        period_start: datetime,
        period_end: datetime,
        totals: UsageSummaryTotals,
        buckets_by_date: dict[date, UsageDailyBucket],
    ) -> None:
        query = (
            select(
                ReceiptRecord.action_intent_record_id,
                ReceiptRecord.created_at,
            )
            .join(
                ActionIntentRecord,
                ActionIntentRecord.action_intent_record_id == ReceiptRecord.action_intent_record_id,
            )
            .where(
                ReceiptRecord.tenant_id == tenant_id,
                ReceiptRecord.created_at >= period_start,
                ReceiptRecord.created_at < period_end,
            )
            .order_by(ReceiptRecord.action_intent_record_id.asc(), ReceiptRecord.created_at.asc())
        )
        if workflow_key is not None:
            query = query.where(ActionIntentRecord.workflow_key == workflow_key)

        first_receipt_at_by_action: dict[str, datetime] = {}
        for action_intent_record_id, event_time in self.session.execute(query):
            event_time_utc = normalize_utc(event_time)
            existing = first_receipt_at_by_action.get(action_intent_record_id)
            if existing is None or event_time_utc < existing:
                first_receipt_at_by_action[action_intent_record_id] = event_time_utc

        for event_time_utc in first_receipt_at_by_action.values():
            bucket = self._bucket_for(buckets_by_date, event_time_utc.date())
            totals.receipt_linked_actions += 1
            bucket.receipt_linked_actions += 1

    def _resolve_period(
        self,
        *,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> tuple[datetime, datetime]:
        if (period_start is None) != (period_end is None):
            raise UsageReportingValidationError(
                "period_start and period_end must be provided together"
            )
        if period_start is None or period_end is None:
            now = utc_now()
            start_at = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return start_at, now

        start_at = normalize_utc(period_start)
        end_at = normalize_utc(period_end)
        if start_at >= end_at:
            raise UsageReportingValidationError("period_end must be later than period_start")
        return start_at, end_at

    def _bucket_for(
        self,
        buckets_by_date: dict[date, UsageDailyBucket],
        usage_date: date,
    ) -> UsageDailyBucket:
        bucket = buckets_by_date.get(usage_date)
        if bucket is None:
            bucket = UsageDailyBucket(usage_date=usage_date)
            buckets_by_date[usage_date] = bucket
        return bucket
