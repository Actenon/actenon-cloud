from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.access import (
    MembershipStatus as MembershipStatus,
)
from app.models.access import (
    Role as Role,
)
from app.models.access import (
    RoleScope as RoleScope,
)
from app.models.access import (
    ServicePrincipal as ServicePrincipal,
)
from app.models.access import (
    ServicePrincipalStatus as ServicePrincipalStatus,
)
from app.models.access import (
    TenantMembership as TenantMembership,
)
from app.models.access import (
    User as User,
)
from app.models.access import (
    UserStatus as UserStatus,
)
from app.models.countersigning import (
    CounterSigningKey as CounterSigningKey,
)
from app.models.countersigning import (
    CounterSigningKeyStatus as CounterSigningKeyStatus,
)
from app.models.countersigning import (
    CounterSigningLifecycleAction as CounterSigningLifecycleAction,
)
from app.models.countersigning import (
    CounterSigningLifecycleRecord as CounterSigningLifecycleRecord,
)
from app.models.countersigning import (
    CounterSigningLifecycleStatus as CounterSigningLifecycleStatus,
)
from app.models.countersigning import (
    CounterSigningOperationRecord as CounterSigningOperationRecord,
)
from app.models.countersigning import (
    CounterSigningOperationStatus as CounterSigningOperationStatus,
)
from app.models.escrow import (
    CapabilityReleaseMode as CapabilityReleaseMode,
)
from app.models.escrow import (
    EscrowRecord as EscrowRecord,
)
from app.models.escrow import (
    EscrowStatus as EscrowStatus,
)
from app.models.escrow import (
    EscrowTransitionRecord as EscrowTransitionRecord,
)
from app.models.escrow import (
    EscrowTransitionType as EscrowTransitionType,
)
from app.models.escrow import (
    ExecutionState as ExecutionState,
)
from app.models.issuance import (
    IssuedProof as IssuedProof,
)
from app.models.issuance import (
    ProofIssuanceStatus as ProofIssuanceStatus,
)
from app.models.issuance import (
    ProofKind as ProofKind,
)
from app.models.issuance import (
    SigningAlgorithm as SigningAlgorithm,
)
from app.models.issuance import (
    SigningKeyBackend as SigningKeyBackend,
)
from app.models.issuance import (
    SigningKeyPurpose as SigningKeyPurpose,
)
from app.models.issuance import (
    SigningKeyReference as SigningKeyReference,
)
from app.models.issuance import (
    SigningKeyStatus as SigningKeyStatus,
)
from app.models.issuance import (
    SigningOperationRecord as SigningOperationRecord,
)
from app.models.issuance import (
    SigningOperationStatus as SigningOperationStatus,
)
from app.models.issuance import (
    TrustTier as TrustTier,
)
from app.models.issuer_registry import (
    IssuerRegistryAuditEvent as IssuerRegistryAuditEvent,
)
from app.models.issuer_registry import (
    IssuerRegistryRecord as IssuerRegistryRecord,
)
from app.models.issuer_registry import (
    IssuerStanding as IssuerStanding,
)
from app.models.issuer_registry import (
    IssuerStatusPublicationRecord as IssuerStatusPublicationRecord,
)
from app.models.issuer_registry import (
    IssuerStatusPublicationStatus as IssuerStatusPublicationStatus,
)
from app.models.receipt_audit import (
    AuditEvent as AuditEvent,
)
from app.models.receipt_audit import (
    ReceiptRecord as ReceiptRecord,
)
from app.models.receipt_audit import (
    ReceiptState as ReceiptState,
)
from app.models.receipt_audit import (
    ReconciliationRecord as ReconciliationRecord,
)
from app.models.receipt_audit import (
    ReconciliationStatus as ReconciliationStatus,
)
from app.models.receipt_audit import (
    ReconciliationType as ReconciliationType,
)
from app.models.transparency import (
    TransparencyCheckpointRecord as TransparencyCheckpointRecord,
)
from app.models.transparency import (
    TransparencyCheckpointStatus as TransparencyCheckpointStatus,
)
from app.models.transparency import (
    TransparencyIntegrityEvent as TransparencyIntegrityEvent,
)
from app.models.transparency import (
    TransparencyLogLeaf as TransparencyLogLeaf,
)
from app.models.transparency import (
    TransparencyLogState as TransparencyLogState,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class TenantStatus(enum.StrEnum):
    active = "active"
    suspended = "suspended"


class FinanceProfile(enum.StrEnum):
    treasury = "treasury"
    payments = "payments"
    mixed_finance = "mixed_finance"


class PolicyStatus(enum.StrEnum):
    draft = "draft"
    active = "active"
    retired = "retired"


class DecisionState(enum.StrEnum):
    allow = "allow"
    deny = "deny"
    approval_required = "approval_required"
    needs_evidence = "needs_evidence"
    structurally_non_executable = "structurally_non_executable"


class ContractValidationStatus(enum.StrEnum):
    valid = "valid"
    invalid = "invalid"
    unsupported = "unsupported"


class ApprovalState(enum.StrEnum):
    not_started = "not_started"
    not_required = "not_required"
    pending = "pending"
    satisfied = "satisfied"
    rejected = "rejected"
    expired = "expired"
    canceled = "canceled"


class EvidenceState(enum.StrEnum):
    not_required = "not_required"
    pending = "pending"
    satisfied = "satisfied"
    expired = "expired"
    canceled = "canceled"


class ApprovalRequestStatus(enum.StrEnum):
    pending = "pending"
    satisfied = "satisfied"
    rejected = "rejected"
    expired = "expired"
    canceled = "canceled"


class ApprovalDecisionType(enum.StrEnum):
    approve = "approve"
    reject = "reject"


class ApprovalAssignmentStatus(enum.StrEnum):
    assigned = "assigned"
    completed = "completed"
    expired = "expired"
    canceled = "canceled"


class EvidenceType(enum.StrEnum):
    document = "document"
    attestation = "attestation"
    external_reference = "external_reference"
    export = "export"
    policy_attachment = "policy_attachment"


class EvidenceStorageMode(enum.StrEnum):
    filesystem = "filesystem"
    object_store = "object_store"
    external_uri = "external_uri"
    inline_metadata_only = "inline_metadata_only"


class EvidenceStatus(enum.StrEnum):
    active = "active"
    expired = "expired"
    revoked = "revoked"


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=TenantStatus.active,
    )
    finance_profile: Mapped[FinanceProfile] = mapped_column(
        Enum(FinanceProfile, native_enum=False, validate_strings=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    policies: Mapped[list[Policy]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    roles: Mapped[list[Role]] = relationship(
        back_populates="tenant",
    )
    memberships: Mapped[list[TenantMembership]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    service_principals: Mapped[list[ServicePrincipal]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    action_intents: Mapped[list[ActionIntentRecord]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    approval_requests: Mapped[list[ApprovalRequest]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    approval_assignments: Mapped[list[ApproverAssignment]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    approval_decisions: Mapped[list[ApprovalDecision]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    evidence_objects: Mapped[list[EvidenceObject]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    escrow_records: Mapped[list[EscrowRecord]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    escrow_transitions: Mapped[list[EscrowTransitionRecord]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    receipt_records: Mapped[list[ReceiptRecord]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    reconciliation_records: Mapped[list[ReconciliationRecord]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "workflow_key",
            "version",
            name="uq_policies_tenant_workflow_version",
        ),
        Index("ix_policies_tenant_workflow_status", "tenant_id", "workflow_key", "status"),
    )

    policy_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_key: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=PolicyStatus.draft,
    )
    default_decision: Mapped[DecisionState] = mapped_column(
        Enum(DecisionState, native_enum=False, validate_strings=True),
        nullable=False,
    )
    finance_action_classes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="policies")
    action_intents: Mapped[list[ActionIntentRecord]] = relationship(back_populates="policy")
    approval_requests: Mapped[list[ApprovalRequest]] = relationship(back_populates="policy")


class ActionIntentRecord(Base):
    __tablename__ = "action_intent_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_action_intent_records_tenant_idempotency_key",
        ),
        UniqueConstraint(
            "tenant_id",
            "submission_id",
            name="uq_action_intent_records_tenant_submission_id",
        ),
        Index("ix_action_intent_records_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_action_intent_records_tenant_workflow", "tenant_id", "workflow_key"),
    )

    action_intent_record_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.policy_id"), nullable=True)
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submission_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_by_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_key: Mapped[str] = mapped_column(String(255), nullable=False)
    external_action_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_family: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_validation_status: Mapped[ContractValidationStatus] = mapped_column(
        Enum(ContractValidationStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    contract_validation_errors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    action_intent_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    action_intent_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    workflow_binding: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    finance_routing_context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    finance_action_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finance_index: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evaluation_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    client_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_state: Mapped[ApprovalState] = mapped_column(
        Enum(ApprovalState, native_enum=False, validate_strings=True),
        nullable=False,
        default=ApprovalState.not_required,
    )
    evidence_state: Mapped[EvidenceState] = mapped_column(
        Enum(EvidenceState, native_enum=False, validate_strings=True),
        nullable=False,
        default=EvidenceState.not_required,
    )
    execution_state: Mapped[ExecutionState] = mapped_column(
        Enum(ExecutionState, native_enum=False, validate_strings=True),
        nullable=False,
        default=ExecutionState.not_requested,
    )
    receipt_state: Mapped[ReceiptState] = mapped_column(
        Enum(ReceiptState, native_enum=False, validate_strings=True),
        nullable=False,
        default=ReceiptState.none,
    )
    latest_receipt_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approval_requirement: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evidence_requirement: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    decision_state: Mapped[DecisionState] = mapped_column(
        Enum(DecisionState, native_enum=False, validate_strings=True),
        nullable=False,
    )
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    matched_rule_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evaluation_trace: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="action_intents")
    policy: Mapped[Policy | None] = relationship(back_populates="action_intents")
    approval_requests: Mapped[list[ApprovalRequest]] = relationship(
        back_populates="action_intent",
        cascade="all, delete-orphan",
    )
    evidence_objects: Mapped[list[EvidenceObject]] = relationship(
        back_populates="action_intent",
        cascade="all, delete-orphan",
    )
    escrow_records: Mapped[list[EscrowRecord]] = relationship(
        back_populates="action_intent",
        cascade="all, delete-orphan",
    )
    receipt_records: Mapped[list[ReceiptRecord]] = relationship(
        back_populates="action_intent",
        cascade="all, delete-orphan",
    )
    reconciliation_records: Mapped[list[ReconciliationRecord]] = relationship(
        back_populates="action_intent",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="action_intent",
        cascade="all, delete-orphan",
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_requests_tenant_status", "tenant_id", "status"),
        Index(
            "ix_approval_requests_action_intent_status",
            "action_intent_record_id",
            "status",
        ),
    )

    approval_request_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    action_intent_record_id: Mapped[str] = mapped_column(
        ForeignKey("action_intent_records.action_intent_record_id"),
        nullable=False,
    )
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.policy_id"), nullable=True)
    workflow_rule_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_group_key: Mapped[str] = mapped_column(String(255), nullable=False)
    required_decision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    eligible_role_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    separation_of_duties: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[ApprovalRequestStatus] = mapped_column(
        Enum(ApprovalRequestStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=ApprovalRequestStatus.pending,
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    satisfied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="approval_requests")
    action_intent: Mapped[ActionIntentRecord] = relationship(back_populates="approval_requests")
    policy: Mapped[Policy | None] = relationship(back_populates="approval_requests")
    assignments: Mapped[list[ApproverAssignment]] = relationship(
        back_populates="approval_request",
        cascade="all, delete-orphan",
    )
    decisions: Mapped[list[ApprovalDecision]] = relationship(
        back_populates="approval_request",
        cascade="all, delete-orphan",
    )
    evidence_objects: Mapped[list[EvidenceObject]] = relationship(
        back_populates="approval_request",
    )


class ApproverAssignment(Base):
    __tablename__ = "approver_assignments"
    __table_args__ = (
        UniqueConstraint(
            "approval_request_id",
            "principal_type",
            "principal_id",
            name="uq_approver_assignments_request_principal",
        ),
        Index(
            "ix_approver_assignments_tenant_principal_status",
            "tenant_id",
            "principal_id",
            "assignment_status",
        ),
    )

    approval_assignment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    approval_request_id: Mapped[str] = mapped_column(
        ForeignKey("approval_requests.approval_request_id"),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    assignment_status: Mapped[ApprovalAssignmentStatus] = mapped_column(
        Enum(ApprovalAssignmentStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=ApprovalAssignmentStatus.assigned,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="approval_assignments")
    approval_request: Mapped[ApprovalRequest] = relationship(back_populates="assignments")


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        UniqueConstraint(
            "approval_request_id",
            "decided_by_principal_type",
            "decided_by_principal_id",
            name="uq_approval_decisions_request_principal",
        ),
        Index("ix_approval_decisions_request_created_at", "approval_request_id", "created_at"),
    )

    approval_decision_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    approval_request_id: Mapped[str] = mapped_column(
        ForeignKey("approval_requests.approval_request_id"),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    decided_by_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    decided_by_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[ApprovalDecisionType] = mapped_column(
        Enum(ApprovalDecisionType, native_enum=False, validate_strings=True),
        nullable=False,
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_object_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="approval_decisions")
    approval_request: Mapped[ApprovalRequest] = relationship(back_populates="decisions")


class EvidenceObject(Base):
    __tablename__ = "evidence_objects"
    __table_args__ = (
        Index("ix_evidence_objects_tenant_action_intent", "tenant_id", "action_intent_record_id"),
        Index("ix_evidence_objects_approval_request", "approval_request_id"),
    )

    evidence_object_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    action_intent_record_id: Mapped[str] = mapped_column(
        ForeignKey("action_intent_records.action_intent_record_id"),
        nullable=False,
    )
    approval_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.approval_request_id"),
        nullable=True,
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, native_enum=False, validate_strings=True),
        nullable=False,
    )
    storage_mode: Mapped[EvidenceStorageMode] = mapped_column(
        Enum(EvidenceStorageMode, native_enum=False, validate_strings=True),
        nullable=False,
    )
    storage_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by_principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    uploaded_by_principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=EvidenceStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="evidence_objects")
    action_intent: Mapped[ActionIntentRecord] = relationship(back_populates="evidence_objects")
    approval_request: Mapped[ApprovalRequest | None] = relationship(
        back_populates="evidence_objects"
    )
