/**
 * Zod schemas mirroring the real actenon-cloud FastAPI response shapes.
 *
 * Source: app/api/action_intents.py, app/api/approvals.py, app/api/receipts.py,
 * app/api/audit.py, app/api/transparency.py Pydantic models.
 *
 * DO NOT invent fields. These mirror the actual backend.
 */
import { z } from 'zod';

// ── Enums (mirror app/models StrEnums) ──────────────────────────────

export const DecisionStateSchema = z.enum([
  'allow',
  'deny',
  'approval_required',
  'needs_evidence',
  'structurally_non_executable',
]);
export type DecisionState = z.infer<typeof DecisionStateSchema>;

export const ApprovalStateSchema = z.enum([
  'not_started',
  'not_required',
  'pending',
  'satisfied',
  'rejected',
  'expired',
  'canceled',
]);
export type ApprovalState = z.infer<typeof ApprovalStateSchema>;

export const EvidenceStateSchema = z.enum([
  'not_required',
  'pending',
  'satisfied',
  'expired',
  'canceled',
]);
export type EvidenceState = z.infer<typeof EvidenceStateSchema>;

export const ExecutionStateSchema = z.enum([
  'not_requested',
  'capability_held',
  'capability_released',
  'dispatch_requested',
  'dispatch_confirmed',
  'result_observed',
  'failure_observed',
  'revoked',
  'quarantined',
  'expired',
]);
export type ExecutionState = z.infer<typeof ExecutionStateSchema>;

export const ReceiptStateSchema = z.enum([
  'none',
  'received',
  'indexed',
  'reconciled',
  'superseded',
]);
export type ReceiptState = z.infer<typeof ReceiptStateSchema>;

export const ContractValidationStatusSchema = z.enum([
  'valid',
  'invalid',
  'unsupported',
]);

export const ApprovalRequestStatusSchema = z.enum([
  'pending',
  'satisfied',
  'rejected',
  'expired',
  'canceled',
]);
export type ApprovalRequestStatus = z.infer<typeof ApprovalRequestStatusSchema>;

export const ApprovalDecisionTypeSchema = z.enum(['approve', 'reject']);

// ── Kernel action intent payload (finance v1alpha1) ─────────────────

export const KernelActionIntentSchema = z.object({
  intent_id: z.string(),
  workflow_key: z.string(),
  action_type: z.string(),
  amount_minor: z.number().int(),
  currency: z.string().length(3),
  source_account_ref: z.string(),
  destination_account_ref: z.string(),
  destination_country: z.string().optional(),
  evidence_refs: z.array(z.string()).optional().default([]),
  requested_execution_date: z.string().optional(),
  metadata: z.record(z.unknown()).optional().default({}),
});
export type KernelActionIntent = z.infer<typeof KernelActionIntentSchema>;

// ── Action intent list item (ActionIntentListItemResponse) ──────────

export const ActionIntentListItemSchema = z.object({
  action_intent_record_id: z.string(),
  tenant_id: z.string(),
  submission_id: z.string(),
  workflow_key: z.string(),
  external_action_intent_id: z.string().nullable(),
  external_reference: z.string().nullable(),
  requested_by_principal_type: z.string(),
  requested_by_principal_id: z.string(),
  finance_action_class: z.string().nullable(),
  amount_minor: z.number().int().nullable(),
  currency: z.string().nullable(),
  source_account_ref: z.string().nullable(),
  destination_account_ref: z.string().nullable(),
  destination_country: z.string().nullable(),
  decision_state: DecisionStateSchema,
  decision_reason: z.string(),
  approval_state: ApprovalStateSchema,
  evidence_state: EvidenceStateSchema,
  execution_state: ExecutionStateSchema,
  receipt_state: ReceiptStateSchema,
  latest_receipt_id: z.string().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type ActionIntentListItem = z.infer<typeof ActionIntentListItemSchema>;

// ── Action intent detail (ActionIntentIntakeResponse) ───────────────

export const ActionIntentDetailSchema = z.object({
  action_intent_record_id: z.string(),
  tenant_id: z.string(),
  policy_id: z.string().nullable(),
  policy_version: z.number().nullable(),
  submission_id: z.string(),
  idempotency_key: z.string(),
  requested_by_principal_type: z.string(),
  requested_by_principal_id: z.string(),
  workflow_key: z.string(),
  external_action_intent_id: z.string().nullable(),
  external_reference: z.string().nullable(),
  contract_family: z.string(),
  contract_version_ref: z.string(),
  contract_validation_status: ContractValidationStatusSchema,
  contract_validation_errors: z.array(z.string()),
  action_intent_digest: z.string(),
  decision_state: DecisionStateSchema,
  decision_reason: z.string(),
  matched_rule_id: z.string().nullable(),
  approval_state: ApprovalStateSchema,
  evidence_state: EvidenceStateSchema,
  execution_state: ExecutionStateSchema,
  receipt_state: ReceiptStateSchema,
  latest_receipt_id: z.string().nullable(),
  approval_requirement: z.record(z.unknown()).nullable(),
  evidence_requirement: z.record(z.unknown()).nullable(),
  workflow_binding: z.record(z.unknown()).nullable(),
  finance_routing_context: z.record(z.unknown()).nullable(),
  finance_action_class: z.string().nullable(),
  finance_index: z.record(z.unknown()),
  action_intent_payload: z.record(z.unknown()),
  evaluation_context: z.record(z.unknown()),
  evaluation_trace: z.array(z.record(z.unknown())),
  client_tags: z.array(z.string()),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  idempotent_replay: z.boolean().default(false),
});
export type ActionIntentDetail = z.infer<typeof ActionIntentDetailSchema>;

// ── Audit trace (FinanceActionTraceResponse) ────────────────────────
// This is the gold mine for the Trust Surface.

export const TraceProofSummarySchema = z.object({
  issued_proof_id: z.string(),
  status: z.string(),
  proof_kind: z.string(),
  audience: z.string(),
  scope: z.array(z.string()),
  nonce: z.string(),
  action_intent_digest: z.string(),
  issued_at: z.string().datetime().nullable(),
  expires_at: z.string().datetime(),
});
export type TraceProofSummary = z.infer<typeof TraceProofSummarySchema>;

export const TraceEscrowSummarySchema = z.object({
  escrow_record_id: z.string(),
  issued_proof_id: z.string(),
  capability_kind: z.string(),
  protected_resource_ref: z.string(),
  status: z.string(),
  execution_state: z.string(),
  provider_execution_ref: z.string().nullable(),
  created_at: z.string().datetime(),
});
export type TraceEscrowSummary = z.infer<typeof TraceEscrowSummarySchema>;

export const TraceReceiptSummarySchema = z.object({
  receipt_id: z.string(),
  issued_proof_id: z.string().nullable(),
  escrow_record_id: z.string().nullable(),
  external_receipt_id: z.string(),
  receipt_type: z.string(),
  outcome: z.string(),
  receipt_timestamp: z.string().datetime(),
  provider_execution_ref: z.string().nullable(),
  receipt_state: z.string(),
  created_at: z.string().datetime(),
});
export type TraceReceiptSummary = z.infer<typeof TraceReceiptSummarySchema>;

export const TraceApprovalRequestSummarySchema = z.object({
  approval_request_id: z.string(),
  status: ApprovalRequestStatusSchema,
  approval_group_key: z.string(),
  required_decision_count: z.number().int(),
  expires_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
});

export const TraceApprovalDecisionSummarySchema = z.object({
  approval_decision_id: z.string(),
  approval_request_id: z.string(),
  decided_by_principal_type: z.string(),
  decided_by_principal_id: z.string(),
  decision: ApprovalDecisionTypeSchema,
  decision_reason: z.string().nullable(),
  evidence_object_ids: z.array(z.string()),
  created_at: z.string().datetime(),
});

export const TraceActionIntentSummarySchema = z.object({
  action_intent_record_id: z.string(),
  tenant_id: z.string(),
  workflow_key: z.string(),
  finance_action_class: z.string().nullable(),
  decision_state: DecisionStateSchema,
  approval_state: ApprovalStateSchema,
  evidence_state: EvidenceStateSchema,
  execution_state: ExecutionStateSchema,
  receipt_state: ReceiptStateSchema,
  latest_receipt_id: z.string().nullable(),
});

export const ReconciliationRecordSchema = z.object({
  reconciliation_record_id: z.string(),
  tenant_id: z.string(),
  action_intent_record_id: z.string(),
  receipt_id: z.string(),
  issued_proof_id: z.string().nullable(),
  escrow_record_id: z.string().nullable(),
  reconciliation_type: z.string(),
  status: z.string(),
  hook_name: z.string(),
  summary: z.string(),
  checks: z.array(z.record(z.unknown())),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export const AuditEventSchema = z.object({
  audit_event_id: z.string(),
  tenant_id: z.string(),
  action_intent_record_id: z.string().nullable(),
  receipt_id: z.string().nullable(),
  issued_proof_id: z.string().nullable(),
  escrow_record_id: z.string().nullable(),
  event_category: z.string(),
  event_type: z.string(),
  subject_type: z.string(),
  subject_id: z.string(),
  actor_principal_type: z.string(),
  actor_principal_id: z.string(),
  event_payload: z.record(z.unknown()),
  created_at: z.string().datetime(),
});

export const FinanceActionTraceSchema = z.object({
  generated_at: z.string().datetime(),
  summary: TraceActionIntentSummarySchema,
  approvals: z.array(TraceApprovalRequestSummarySchema),
  approval_decisions: z.array(TraceApprovalDecisionSummarySchema),
  evidence_objects: z.array(z.record(z.unknown())),
  issued_proofs: z.array(TraceProofSummarySchema),
  escrow_records: z.array(TraceEscrowSummarySchema),
  receipts: z.array(TraceReceiptSummarySchema),
  reconciliation_records: z.array(ReconciliationRecordSchema),
  audit_events: z.array(AuditEventSchema),
});
export type FinanceActionTrace = z.infer<typeof FinanceActionTraceSchema>;

// ── Receipt detail (ReceiptResponse) ────────────────────────────────

export const ReceiptDetailSchema = z.object({
  receipt_id: z.string(),
  tenant_id: z.string(),
  action_intent_record_id: z.string(),
  issued_proof_id: z.string().nullable(),
  escrow_record_id: z.string().nullable(),
  contract_family: z.string(),
  contract_version_ref: z.string(),
  contract_validation_status: z.string(),
  contract_validation_errors: z.array(z.string()),
  external_receipt_id: z.string(),
  receipt_type: z.string(),
  outcome: z.string(),
  receipt_timestamp: z.string().datetime(),
  kernel_receipt_digest: z.string(),
  receipt_payload: z.record(z.unknown()),
  receipt_index: z.record(z.unknown()),
  linked_approval_request_ids: z.array(z.string()),
  linked_approval_decision_ids: z.array(z.string()),
  linked_evidence_object_ids: z.array(z.string()),
  provider_execution_ref: z.string().nullable(),
  settlement_reference: z.string().nullable(),
  received_by_principal_type: z.string(),
  received_by_principal_id: z.string(),
  receipt_state: ReceiptStateSchema,
  reconciliation_summary: z.record(z.unknown()),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  idempotent_replay: z.boolean().default(false),
});
export type ReceiptDetail = z.infer<typeof ReceiptDetailSchema>;

// ── Approval request (ApprovalRequestResponse) ──────────────────────

export const ApprovalAssignmentSchema = z.object({
  approval_assignment_id: z.string(),
  principal_type: z.string(),
  principal_id: z.string(),
  assignment_status: z.string(),
  assigned_at: z.string().datetime(),
  acted_at: z.string().datetime().nullable(),
});

export const ApprovalDecisionSchema = z.object({
  approval_decision_id: z.string(),
  decided_by_principal_type: z.string(),
  decided_by_principal_id: z.string(),
  decision: ApprovalDecisionTypeSchema,
  decision_reason: z.string().nullable(),
  evidence_object_ids: z.array(z.string()),
  created_at: z.string().datetime(),
});

export const ApprovalRequestSchema = z.object({
  approval_request_id: z.string(),
  tenant_id: z.string(),
  action_intent_record_id: z.string(),
  policy_id: z.string().nullable(),
  workflow_rule_id: z.string().nullable(),
  approval_group_key: z.string(),
  required_decision_count: z.number().int(),
  eligible_role_ids: z.array(z.string()),
  separation_of_duties: z.record(z.boolean()),
  status: ApprovalRequestStatusSchema,
  decision_reason: z.string().nullable(),
  expires_at: z.string().datetime().nullable(),
  satisfied_at: z.string().datetime().nullable(),
  rejected_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  assignments: z.array(ApprovalAssignmentSchema),
  decisions: z.array(ApprovalDecisionSchema),
});
export type ApprovalRequest = z.infer<typeof ApprovalRequestSchema>;

// ── Transparency / chain verification ───────────────────────────────

export const InclusionProofResponseSchema = z.object({
  proof: z.record(z.unknown()),
  checkpoint: z.record(z.unknown()),
});
export type InclusionProofResponse = z.infer<typeof InclusionProofResponseSchema>;

// ── Auth session ────────────────────────────────────────────────────

export const TenantAccessSchema = z.object({
  tenant_id: z.string(),
  role_names: z.array(z.string()),
  permissions: z.array(z.string()),
});

export const AuthSessionSchema = z.object({
  principal_type: z.string(),
  principal_id: z.string(),
  display_name: z.string(),
  token_kind: z.string(),
  auth_mode: z.string(),
  issued_at: z.string().datetime(),
  expires_at: z.string().datetime(),
  platform_roles: z.array(z.string()),
  platform_permissions: z.array(z.string()),
  tenant_access: z.array(TenantAccessSchema),
});
export type AuthSession = z.infer<typeof AuthSessionSchema>;
