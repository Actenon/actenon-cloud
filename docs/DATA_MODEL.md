# Data Model

## Purpose

This document defines the logical data model for Actenon Cloud. It focuses on durable business records and state separation, not physical database implementation.

## Modeling Principles

- Canonical kernel artifacts are stored immutably and referenced by digest plus version.
- Control-plane governance state is modeled separately from kernel execution state.
- State axes are split so approval, proof issuance, execution observation, and receipt ingestion do not collapse into a single overloaded status field.
- Finance-specific search fields are treated as derived indexes, not canonical replacements for the kernel Action Intent payload.
- Every tenant-scoped row must carry a `tenant_id`.

## State Axes

The control plane should use separate state axes on `ActionIntentRecord` and related artifacts.

| State Axis | Meaning | Owner |
| --- | --- | --- |
| `intake_state` | Submission validation and admission posture inside the control plane | Control plane |
| `approval_state` | Approval workflow progress and outcome | Control plane |
| `proof_state` | Whether a proof or PCCB is eligible, requested, issued, failed, or revoked | Control plane |
| `execution_state` | Coarse control-plane lifecycle around capability release and external execution progress | Control plane observation only |
| `escrow_state` | Capability custody and release state on `EscrowRecord` | Control plane |
| `receipt_state` | Whether a kernel-aligned receipt has been received, indexed, and reconciled | Control plane |
| `artifact_control_state` | Whether an artifact is active, quarantined, released, or revoked | Control plane |

## Core Entity Definitions

### Tenant

| Field | Type | Notes |
| --- | --- | --- |
| `tenant_id` | string | Stable primary identifier |
| `display_name` | string | Tenant-visible name |
| `status` | enum | `ACTIVE`, `SUSPENDED`, `DECOMMISSIONING`, `DECOMMISSIONED` |
| `finance_profile` | enum | Narrow Release 1 domain profile, for example `TREASURY`, `PAYMENTS`, `MIXED_FINANCE` |
| `default_policy_pack_id` | string nullable | Default approval and control profile |
| `created_at` | timestamp | Audit baseline |
| `updated_at` | timestamp | Last metadata update |

### User

| Field | Type | Notes |
| --- | --- | --- |
| `user_id` | string | Stable identity key |
| `identity_provider_subject` | string | External IdP subject or login mapping |
| `email` | string | Operator or approver contact |
| `status` | enum | `ACTIVE`, `DISABLED`, `LOCKED` |
| `created_at` | timestamp | Audit baseline |
| `updated_at` | timestamp | Last metadata update |

### Role

| Field | Type | Notes |
| --- | --- | --- |
| `role_id` | string | Stable role identifier |
| `tenant_id` | string nullable | Null for platform-scoped template roles, populated for tenant-local roles |
| `name` | string | Human-readable role name |
| `permissions` | set | Permission bundle, not a free-form narrative |
| `approval_entitlements` | set | Finance approval capabilities and thresholds |
| `created_at` | timestamp | Audit baseline |

### TenantMembership

| Field | Type | Notes |
| --- | --- | --- |
| `membership_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `user_id` | string | User scope |
| `role_ids` | array | Effective tenant roles |
| `membership_status` | enum | `ACTIVE`, `INVITED`, `SUSPENDED`, `REMOVED` |
| `approver_profile` | json object nullable | Optional thresholds, approval classes, or limits |
| `created_at` | timestamp | Audit baseline |
| `updated_at` | timestamp | Last metadata update |

### PolicyPack

| Field | Type | Notes |
| --- | --- | --- |
| `policy_pack_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `version` | integer | Monotonic version |
| `name` | string | Human-readable policy name |
| `status` | enum | `DRAFT`, `ACTIVE`, `RETIRED` |
| `finance_action_classes` | array | Release 1 focus such as `payment`, `transfer`, `settlement_instruction` |
| `rule_set_ref` | string | Internal pointer to workflow rules bundle |
| `created_by_user_id` | string | Policy author |
| `created_at` | timestamp | Audit baseline |
| `activated_at` | timestamp nullable | Becomes live |

### WorkflowRule

| Field | Type | Notes |
| --- | --- | --- |
| `workflow_rule_id` | string | Stable identifier |
| `policy_pack_id` | string | Parent policy pack |
| `rule_type` | enum | `APPROVAL_THRESHOLD`, `EVIDENCE_REQUIREMENT`, `SEGREGATION_OF_DUTIES`, `TIME_WINDOW`, `PROOF_REQUIREMENT`, `ESCROW_REQUIREMENT` |
| `priority` | integer | Evaluation order |
| `condition_expression` | structured expression | Rule predicate evaluated against tenant, actor, finance index, and submission context |
| `outcome_definition` | structured object | Required approvals, evidence classes, or downstream control actions |
| `effective_from` | timestamp | Start time |
| `effective_to` | timestamp nullable | End time |

### ActionIntentRecord

| Field | Type | Notes |
| --- | --- | --- |
| `action_intent_record_id` | string | Control-plane record identifier |
| `tenant_id` | string | Tenant scope |
| `submission_id` | string | Client-visible submission identifier |
| `idempotency_key` | string | Deduplicates intake |
| `submitted_by_principal_id` | string | User or service principal reference |
| `kernel_contract_ref` | string | Pinned reference to kernel Action Intent schema or artifact version |
| `kernel_action_intent_payload_ref` | string | Immutable pointer to stored canonical payload |
| `kernel_action_intent_digest` | string | Integrity digest for payload |
| `finance_action_class` | enum | Derived routing index such as `payment`, `transfer`, `payout`, `collection`, `settlement_instruction` |
| `finance_index` | json object nullable | Derived search fields like amount, currency, source account, destination account |
| `policy_pack_id` | string nullable | Policy pack selected at intake |
| `workflow_instance_id` | string nullable | Approval workflow grouping key |
| `intake_state` | enum | Control-plane admission state |
| `approval_state` | enum | Approval state axis |
| `proof_state` | enum | Proof issuance state axis |
| `execution_state` | enum | Coarse execution observation state |
| `receipt_state` | enum | Receipt ingestion and indexing state |
| `latest_receipt_id` | string nullable | Most recent linked receipt |
| `latest_proof_id` | string nullable | Most recent linked proof |
| `created_at` | timestamp | Intake timestamp |
| `updated_at` | timestamp | Last control-plane mutation |

### EvidenceObject

| Field | Type | Notes |
| --- | --- | --- |
| `evidence_object_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `action_intent_record_id` | string nullable | Linked intent |
| `evidence_type` | enum | `DOCUMENT`, `ATTESTATION`, `EXTERNAL_REFERENCE`, `EXPORT`, `POLICY_ATTACHMENT` |
| `storage_mode` | enum | `FILESYSTEM`, `OBJECT_STORE`, `EXTERNAL_URI`, `INLINE_METADATA_ONLY` |
| `storage_ref` | string | Filesystem-relative path, object key, or external reference |
| `content_digest` | string nullable | Integrity digest |
| `captured_by_principal_id` | string | Uploader or registrar |
| `retention_class` | enum | Retention or custody tier |
| `artifact_control_state` | enum | Active, quarantined, revoked, released |
| `created_at` | timestamp | Registration time |

### ApprovalRequest

| Field | Type | Notes |
| --- | --- | --- |
| `approval_request_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `action_intent_record_id` | string | Linked intent |
| `policy_pack_id` | string | Generating policy |
| `workflow_rule_id` | string nullable | Source rule |
| `approval_group_key` | string | Groups parallel approvers |
| `required_decision_count` | integer | Number of decisions needed |
| `eligible_role_ids` | array | Roles allowed to decide |
| `status` | enum | `PENDING`, `SATISFIED`, `REJECTED`, `EXPIRED`, `CANCELED` |
| `expires_at` | timestamp nullable | Deadline |
| `created_at` | timestamp | Creation time |

### ApprovalDecision

| Field | Type | Notes |
| --- | --- | --- |
| `approval_decision_id` | string | Stable identifier |
| `approval_request_id` | string | Linked request |
| `tenant_id` | string | Tenant scope |
| `decided_by_principal_id` | string | User or service principal |
| `decision` | enum | `APPROVE`, `REJECT`, `ABSTAIN` |
| `decision_reason` | string nullable | Human or machine reason |
| `evidence_object_ids` | array nullable | Evidence cited by approver |
| `created_at` | timestamp | Decision time |

### IssuedProof

| Field | Type | Notes |
| --- | --- | --- |
| `issued_proof_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `action_intent_record_id` | string | Linked intent |
| `proof_kind` | enum | `PCCB`, `APPROVAL_ATTESTATION`, `EVIDENCE_MANIFEST`, `EXPORT_SIGNATURE` |
| `kernel_artifact_refs` | array | Linked kernel proofs or receipts if present |
| `proof_payload_ref` | string | Stored proof bundle reference |
| `proof_digest` | string | Integrity digest |
| `signing_key_reference_id` | string nullable | Managed key used for signing |
| `proof_state` | enum | `NOT_REQUESTED`, `ELIGIBLE`, `ISSUANCE_REQUESTED`, `ISSUED`, `FAILED`, `REVOKED` |
| `issued_at` | timestamp nullable | When issued |

### SigningKeyReference

| Field | Type | Notes |
| --- | --- | --- |
| `signing_key_reference_id` | string | Stable identifier |
| `tenant_id` | string nullable | Tenant-local or platform-shared scope |
| `provider_key_ref` | string | External KMS or HSM key reference |
| `key_purpose` | enum | `PCCB_SIGNING`, `ATTESTATION_SIGNING`, `EXPORT_SIGNING` |
| `algorithm` | enum | Provider-supported algorithm label |
| `status` | enum | `ACTIVE`, `ROTATING`, `SUSPENDED`, `REVOKED`, `RETIRED` |
| `rotation_policy_ref` | string nullable | Rotation policy link |
| `attestation_ref` | string nullable | Provider attestation or custody record |
| `created_at` | timestamp | Registration time |
| `rotated_at` | timestamp nullable | Most recent rotation |

### EscrowRecord

| Field | Type | Notes |
| --- | --- | --- |
| `escrow_record_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `action_intent_record_id` | string | Linked intent |
| `issued_proof_id` | string | Bound proof that authorizes release |
| `capability_kind` | string | Narrow finance capability class such as `finance.transfer.release` |
| `protected_resource_ref` | string | Provider or protected resource surface |
| `release_mode` | enum | `DEVELOPMENT_SIMULATED`, `EXTERNAL_MANAGED` |
| `status` | enum | `HELD`, `RELEASED`, `CONSUMED`, `REVOKED`, `QUARANTINED`, `EXPIRED` |
| `execution_state` | enum | `CAPABILITY_HELD`, `CAPABILITY_RELEASED`, `DISPATCH_REQUESTED`, `DISPATCH_CONFIRMED`, `RESULT_OBSERVED`, `FAILURE_OBSERVED`, `REVOKED`, `QUARANTINED`, `EXPIRED` |
| `audience` | string | Copied from issued proof binding |
| `scope` | array | Copied from issued proof binding |
| `scope_hash` | string | Digest for exact scope binding |
| `action_intent_digest` | string | Exact bound action hash |
| `capability_reference` | string nullable | Stable release handle |
| `capability_token_digest` | string nullable | Stored digest of the one-time capability token |
| `provider_execution_ref` | string nullable | Downstream execution correlation |
| `created_at` | timestamp | Creation time |
| `updated_at` | timestamp | Last status change |

### ReceiptRecord

| Field | Type | Notes |
| --- | --- | --- |
| `receipt_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `action_intent_record_id` | string nullable | Linked intent if correlation exists |
| `kernel_contract_ref` | string | Pinned kernel receipt schema or artifact version |
| `kernel_receipt_payload_ref` | string | Immutable stored receipt payload reference |
| `kernel_receipt_digest` | string | Integrity digest |
| `receipt_type` | string | Kernel-defined type stored as indexed string |
| `receipt_timestamp` | timestamp | Kernel-emitted or observed time |
| `index_fields` | json object | Query indexes derived without mutating canonical fields |
| `receipt_state` | enum | `NONE`, `RECEIVED`, `INDEXED`, `RECONCILED`, `SUPERSEDED` |
| `artifact_control_state` | enum | Active, quarantined, revoked, released |
| `created_at` | timestamp | Ingestion time |

### ReplayConsumptionState

| Field | Type | Notes |
| --- | --- | --- |
| `replay_consumption_state_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `consumer_name` | string | Internal consumer or workflow name |
| `receipt_id` | string nullable | Last consumed receipt |
| `stream_cursor` | string nullable | Offset, watermark, or cursor |
| `status` | enum | `IDLE`, `IN_PROGRESS`, `FAILED`, `COMPLETE` |
| `last_error` | string nullable | Most recent failure |
| `updated_at` | timestamp | Last checkpoint |

### ProviderExecutionHook

| Field | Type | Notes |
| --- | --- | --- |
| `provider_execution_hook_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `action_intent_record_id` | string | Linked intent |
| `hook_type` | enum | `OUTBOUND_REQUEST`, `INBOUND_CALLBACK`, `STATUS_POLL`, `ACKNOWLEDGMENT` |
| `provider_ref` | string | External provider or adapter identifier |
| `provider_correlation_id` | string nullable | External correlation key |
| `hook_status` | enum | `CREATED`, `SENT`, `ACKNOWLEDGED`, `FAILED`, `IGNORED` |
| `payload_ref` | string nullable | Stored payload reference |
| `observed_at` | timestamp | Event timestamp |

### ReconciliationRecord

| Field | Type | Notes |
| --- | --- | --- |
| `reconciliation_record_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `action_intent_record_id` | string nullable | Linked intent |
| `receipt_id` | string nullable | Linked receipt |
| `reconciliation_type` | enum | `INTENT_TO_RECEIPT`, `PROOF_TO_RECEIPT`, `EXPORT_TO_AUDIT`, `PROVIDER_TO_RECEIPT` |
| `status` | enum | `PENDING`, `MATCHED`, `MISMATCHED`, `MANUAL_REVIEW_REQUIRED`, `CLOSED` |
| `expected_ref` | string | Expected artifact or business key |
| `observed_ref` | string nullable | Observed artifact or business key |
| `details_ref` | string nullable | Stored reconciliation evidence |
| `created_at` | timestamp | Creation time |
| `updated_at` | timestamp | Last evaluation |

### AuditEvent

| Field | Type | Notes |
| --- | --- | --- |
| `audit_event_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `actor_principal_id` | string nullable | User, service principal, or system actor |
| `event_type` | string | Stable event name |
| `subject_type` | string | Entity class under change |
| `subject_id` | string | Entity identifier |
| `event_time` | timestamp | Event time |
| `event_payload_ref` | string nullable | Large payload or diff location |
| `trace_id` | string nullable | Observability correlation |

### ArtifactControlState

| Field | Type | Notes |
| --- | --- | --- |
| `artifact_control_state_id` | string | Stable identifier |
| `tenant_id` | string | Tenant scope |
| `subject_type` | enum | `EVIDENCE_OBJECT`, `ISSUED_PROOF`, `RECEIPT`, `ESCROW_RECORD` |
| `subject_id` | string | Target artifact |
| `state` | enum | `ACTIVE`, `QUARANTINED`, `RELEASED`, `REVOKED` |
| `reason_code` | string | Policy or operator reason |
| `imposed_by_principal_id` | string nullable | Human or system actor |
| `imposed_at` | timestamp | State change time |
| `released_at` | timestamp nullable | Optional release time |
| `notes_ref` | string nullable | Stored supporting material |

## Cardinality Summary

- One tenant has many users through memberships.
- One tenant has many policy packs; one active policy pack may apply to many intents.
- One Action Intent record may have many evidence objects, approval requests, receipts, audit events, provider hooks, and reconciliation records.
- One approval request may have many approval decisions.
- One Action Intent record may have zero or many issued proofs and escrow records.
- One governed artifact may have many artifact control events over time, but only one current effective state.

## Storage Shape Recommendation

The recommended storage pattern is:

- relational rows for metadata, links, indexes, and state axes
- immutable object storage for large canonical payloads, evidence, proofs, and export bundles
- digest-based integrity references between relational records and immutable objects

## Intentionally Deferred Physical Design

This document does not lock in:

- table partitioning strategy
- exact SQL dialect
- event bus design
- queue implementation
- object-store vendor
- whether some records become append-only event streams versus mutable summary rows
