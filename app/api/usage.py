from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies import get_auth_service, get_current_session, get_usage_service
from app.services.auth import (
    TENANT_AUDIT_READ,
    AuthenticatedSession,
    AuthorizationError,
    AuthService,
)
from app.services.usage import (
    TenantUsageReport,
    UsageDailyBucket,
    UsageDefinitions,
    UsageReportingValidationError,
    UsageService,
    UsageSummaryTotals,
)

router = APIRouter(prefix="/usage", tags=["usage"])


class UsageSummaryTotalsResponse(BaseModel):
    submitted_actions: int
    billable_proved_and_allowed_actions: int
    blocked_or_refused_actions: int
    blocked_policy_actions: int
    structurally_refused_actions: int
    held_for_review_actions: int
    reviewed_actions: int
    receipt_linked_actions: int


class UsageDailyBucketResponse(BaseModel):
    usage_date: date
    submitted_actions: int
    billable_proved_and_allowed_actions: int
    blocked_or_refused_actions: int
    held_for_review_actions: int
    reviewed_actions: int
    receipt_linked_actions: int


class UsageDefinitionsResponse(BaseModel):
    pricing_status: str
    billable_action_definition: str
    blocked_action_definition: str
    reviewed_action_definition: str
    receipt_linked_definition: str


class TenantUsageReportResponse(BaseModel):
    generated_at: datetime
    tenant_id: str
    workflow_key: str | None
    period_start: datetime
    period_end: datetime
    totals: UsageSummaryTotalsResponse
    daily_buckets: list[UsageDailyBucketResponse]
    definitions: UsageDefinitionsResponse


def _to_totals_response(totals: UsageSummaryTotals) -> UsageSummaryTotalsResponse:
    return UsageSummaryTotalsResponse(
        submitted_actions=totals.submitted_actions,
        billable_proved_and_allowed_actions=totals.billable_proved_and_allowed_actions,
        blocked_or_refused_actions=totals.blocked_or_refused_actions,
        blocked_policy_actions=totals.blocked_policy_actions,
        structurally_refused_actions=totals.structurally_refused_actions,
        held_for_review_actions=totals.held_for_review_actions,
        reviewed_actions=totals.reviewed_actions,
        receipt_linked_actions=totals.receipt_linked_actions,
    )


def _to_bucket_response(bucket: UsageDailyBucket) -> UsageDailyBucketResponse:
    return UsageDailyBucketResponse(
        usage_date=bucket.usage_date,
        submitted_actions=bucket.submitted_actions,
        billable_proved_and_allowed_actions=bucket.billable_proved_and_allowed_actions,
        blocked_or_refused_actions=bucket.blocked_or_refused_actions,
        held_for_review_actions=bucket.held_for_review_actions,
        reviewed_actions=bucket.reviewed_actions,
        receipt_linked_actions=bucket.receipt_linked_actions,
    )


def _to_definitions_response(definitions: UsageDefinitions) -> UsageDefinitionsResponse:
    return UsageDefinitionsResponse(
        pricing_status=definitions.pricing_status,
        billable_action_definition=definitions.billable_action_definition,
        blocked_action_definition=definitions.blocked_action_definition,
        reviewed_action_definition=definitions.reviewed_action_definition,
        receipt_linked_definition=definitions.receipt_linked_definition,
    )


def _to_report_response(report: TenantUsageReport) -> TenantUsageReportResponse:
    definitions = report.definitions
    if definitions is None:
        raise RuntimeError("usage report definitions were not populated")
    return TenantUsageReportResponse(
        generated_at=report.generated_at,
        tenant_id=report.tenant_id,
        workflow_key=report.workflow_key,
        period_start=report.period_start,
        period_end=report.period_end,
        totals=_to_totals_response(report.totals),
        daily_buckets=[_to_bucket_response(bucket) for bucket in report.daily_buckets],
        definitions=_to_definitions_response(definitions),
    )


@router.get("/summary", response_model=TenantUsageReportResponse)
def get_usage_summary(
    service: Annotated[UsageService, Depends(get_usage_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    auth_session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    tenant_id: str | None = Query(default=None),
    workflow_key: str | None = Query(default="payments.standard"),
    period_start: datetime | None = Query(default=None),
    period_end: datetime | None = Query(default=None),
) -> TenantUsageReportResponse:
    try:
        tenant_id = auth_service.require_tenant_query_scope(
            auth_session,
            tenant_id=tenant_id,
            permission=TENANT_AUDIT_READ,
        )
        report = service.build_usage_report(
            tenant_id=tenant_id,
            workflow_key=workflow_key,
            period_start=period_start,
            period_end=period_end,
        )
        return _to_report_response(report)
    except UsageReportingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
