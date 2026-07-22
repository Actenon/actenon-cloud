/**
 * Canned demo incidents for the Trust Surface "replay as demo" affordance.
 *
 * These mirror the REAL backend response shapes (same zod schemas).
 * They let a stranger see the incident-to-containment story with zero setup.
 *
 * The flagship scenario: subscription-cancel-refused — an agent attempts to
 * cancel a $99,999 transfer while authorised only for $20. The PCCB bound
 * $20.00 → attempted $99,999.00 → REFUSED (ACTION_MISMATCH) before execution.
 */

import type { FinanceActionTrace } from './schemas';

const NOW = '2026-07-14T10:42:17.000Z';
const EARLIER = '2026-07-14T10:41:55.000Z';

export const DEMO_TRACE: FinanceActionTrace = {
  generated_at: NOW,
  summary: {
    action_intent_record_id: 'air_01J4DGHP9XKQFM7S3VRZN8BW6A',
    tenant_id: 'tnt_acme',
    workflow_key: 'subscription.billing.cancel',
    finance_action_class: 'transfer',
    decision_state: 'deny',
    approval_state: 'not_required',
    evidence_state: 'not_required',
    execution_state: 'not_requested',
    receipt_state: 'none',
    latest_receipt_id: null,
  },
  approvals: [],
  approval_decisions: [],
  evidence_objects: [],
  issued_proofs: [
    {
      issued_proof_id: 'prf_01J4DGHP8W3NKBZ5T2YQM9CXJ7',
      status: 'issued',
      proof_kind: 'pccb',
      audience: 'actenon-permit-gateway',
      scope: ['transfer:execute'],
      nonce: '9f2a8c1e4b7d6034',
      action_intent_digest:
        'sha256:a3f1c8d9e2b47065893f12da4567890bcdef0123456789abcdef0123456789ab',
      issued_at: EARLIER,
      expires_at: '2026-07-14T11:41:55.000Z',
    },
  ],
  escrow_records: [],
  receipts: [],
  reconciliation_records: [],
  audit_events: [
    {
      audit_event_id: 'aev_01J4DGHPB2RFN4T8KM5VQX7WZ3',
      tenant_id: 'tnt_acme',
      action_intent_record_id: 'air_01J4DGHP9XKQFM7S3VRZN8BW6A',
      receipt_id: null,
      issued_proof_id: 'prf_01J4DGHP8W3NKBZ5T2YQM9CXJ7',
      escrow_record_id: null,
      event_category: 'decision',
      event_type: 'action_intent.refused',
      subject_type: 'action_intent',
      subject_id: 'air_01J4DGHP9XKQFM7S3VRZN8BW6A',
      actor_principal_type: 'service_principal',
      actor_principal_id: 'svc_refund_bot_07',
      event_payload: {
        failure_code: 'ACTION_MISMATCH',
        authorised_amount_minor: 2000,
        attempted_amount_minor: 9999900,
        currency: 'USD',
      },
      created_at: NOW,
    },
  ],
};

export const DEMO_ACTION_INTENT = {
  action_intent_record_id: 'air_01J4DGHP9XKQFM7S3VRZN8BW6A',
  tenant_id: 'tnt_acme',
  policy_id: 'pol_subscription_cancel_v3',
  policy_version: 3,
  submission_id: 'sub_01J4DGHP5R2M',
  idempotency_key: 'idem_20260714_refund_bot_07_001',
  requested_by_principal_type: 'service_principal',
  requested_by_principal_id: 'svc_refund_bot_07',
  workflow_key: 'subscription.billing.cancel',
  external_action_intent_id: null,
  external_reference: 'stripe_sub_1Nq8ZkBJ9c',
  contract_family: 'action_intent',
  contract_version_ref: 'finance.v1alpha1',
  contract_validation_status: 'valid' as const,
  contract_validation_errors: [],
  action_intent_digest:
    'sha256:a3f1c8d9e2b47065893f12da4567890bcdef0123456789abcdef0123456789ab',
  decision_state: 'deny' as const,
  decision_reason: 'ACTION_MISMATCH: authorised amount $20.00 but attempted $99,999.00',
  matched_rule_id: 'rule_amount_cap_20',
  approval_state: 'not_required' as const,
  evidence_state: 'not_required' as const,
  execution_state: 'not_requested' as const,
  receipt_state: 'none' as const,
  latest_receipt_id: null,
  approval_requirement: null,
  evidence_requirement: null,
  workflow_binding: {
    policy_pack_id: 'ppk_finance_ops_v2',
    workflow_profile: 'standard',
    requested_execution_window: null,
  },
  finance_routing_context: {
    action_class: 'transfer',
    amount_minor: 9999900,
    currency: 'USD',
    source_account_ref: 'acct_operating',
    destination_account_ref: 'acct_customer_8821',
    risk_tier: 'high',
  },
  finance_action_class: 'transfer',
  finance_index: {
    amount_minor: 9999900,
    currency: 'USD',
    source_account_ref: 'acct_operating',
    destination_account_ref: 'acct_customer_8821',
    destination_country: 'GB',
  },
  action_intent_payload: {
    intent_id: 'int_01J4DGHP9XKQFM7S3',
    workflow_key: 'subscription.billing.cancel',
    action_type: 'transfer',
    amount_minor: 9999900,
    currency: 'USD',
    source_account_ref: 'acct_operating',
    destination_account_ref: 'acct_customer_8821',
    destination_country: 'GB',
    evidence_refs: [],
    metadata: { subscription_id: 'sub_1Nq8ZkBJ9c' },
  },
  evaluation_context: {
    grant_id: 'grnt_01J4DGFM2R8V',
    grant_scopes: ['transfer:execute'],
    grant_budget_remaining_minor: 2000,
    grant_amount_cap_minor: 2000,
    grant_currency: 'USD',
    grant_expires_at: '2026-07-15T10:00:00Z',
    pccb_bound_amount_minor: 2000,
    pccb_bound_target: 'acct_customer_8821',
  },
  evaluation_trace: [
    { step: 1, check: 'grant_signature', result: 'pass' },
    { step: 2, check: 'grant_revoked', result: 'pass' },
    { step: 3, check: 'grant_expired', result: 'pass' },
    { step: 4, check: 'scope_allowed', result: 'pass', scope: 'transfer:execute' },
    { step: 5, check: 'amount_within_cap', result: 'fail', authorised_minor: 2000, attempted_minor: 9999900 },
    { step: 6, check: 'budget_remaining', result: 'skip', reason: 'amount_cap_failed' },
    { step: 7, check: 'pccb_bound', result: 'fail', failure_code: 'ACTION_MISMATCH' },
    { step: 8, check: 'dedup_replay', result: 'skip', reason: 'prior_failure' },
  ],
  client_tags: ['env:production', 'agent:refund-bot-7'],
  created_at: EARLIER,
  updated_at: NOW,
  idempotent_replay: false,
};

export const DEMO_RECEIPT = {
  receipt_id: 'rcp_01J4DGHP9XKQFM7S3VRZN8BW6A',
  tenant_id: 'tnt_acme',
  action_intent_record_id: 'air_01J4DGHP9XKQFM7S3VRZN8BW6A',
  issued_proof_id: 'prf_01J4DGHP8W3NKBZ5T2YQM9CXJ7',
  escrow_record_id: null,
  contract_family: 'receipt',
  contract_version_ref: 'finance.v1alpha1',
  contract_validation_status: 'valid',
  contract_validation_errors: [],
  external_receipt_id: 'rcpt_01J4DGHPB2RFN4T8',
  receipt_type: 'refusal_record',
  outcome: 'refused_before_execution',
  receipt_timestamp: NOW,
  kernel_receipt_digest:
    'sha256:e7b4c1d9f3a82056749102ef8456ab90cdef1234567890abcdef1234567890ab',
  receipt_payload: {
    failure_code: 'ACTION_MISMATCH',
    authority_boundary: {
      authorised_action_hash: 'sha256:b2f4e8c1d9a305674891f02e8456ab90cdef1234567890abcdef1234567890cd',
      attempted_action_hash: 'sha256:9c1e7d4b2a806f355749102ef8456ab90cdef1234567890abcdef1234567890ef',
      match: false,
    },
    signing_key_id: 'ks_ed25519_2026q3',
    signing_algorithm: 'EdDSA',
  },
  receipt_index: {
    leaf_index: 4821,
    log_id: 'actenon-transparency-log',
  },
  linked_approval_request_ids: [],
  linked_approval_decision_ids: [],
  linked_evidence_object_ids: [],
  provider_execution_ref: null,
  settlement_reference: null,
  received_by_principal_type: 'service_principal',
  received_by_principal_id: 'svc_permit_gateway',
  receipt_state: 'received' as const,
  reconciliation_summary: {
    intent_to_receipt: 'verified',
    proof_to_receipt: 'verified',
    cost_actual_minor: null,
    cost_reserved_minor: null,
  },
  created_at: NOW,
  updated_at: NOW,
  idempotent_replay: false,
};
