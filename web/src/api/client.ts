/**
 * Typed API client for actenon-cloud.
 *
 * All responses are parsed through zod schemas mirroring the backend.
 * Auth token is read from localStorage (set by the dev-auth bar) or
 * the VITE_API_TOKEN env var. In production, OIDC sets the token.
 */

import {
  ActionIntentDetailSchema,
  ActionIntentListItemSchema,
  ApprovalRequestSchema,
  AuthSessionSchema,
  FinanceActionTraceSchema,
  InclusionProofResponseSchema,
  ReceiptDetailSchema,
  type ActionIntentDetail,
  type ActionIntentListItem,
  type ApprovalRequest,
  type ApprovalRequestStatus,
  type AuthSession,
  type DecisionState,
  type FinanceActionTrace,
  type InclusionProofResponse,
  type ReceiptDetail,
} from './schemas';

const API_PREFIX = '/api/v1';
const TOKEN_KEY = 'actenon.dev-token';

export function getToken(): string | null {
  return (
    (import.meta as unknown as { env?: { VITE_API_TOKEN?: string } }).env?.VITE_API_TOKEN ??
    localStorage.getItem(TOKEN_KEY) ??
    null
  );
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function requestOne<T>(
  path: string,
  schema: { parse: (data: unknown) => T },
  init?: RequestInit,
): Promise<T> {
  return doFetch(path, schema, init, false) as Promise<T>;
}

async function requestMany<T>(
  path: string,
  schema: { parse: (data: unknown) => T },
  init?: RequestInit,
): Promise<T[]> {
  return doFetch(path, schema, init, true) as Promise<T[]>;
}

async function doFetch<T>(
  path: string,
  schema: { parse: (data: unknown) => T },
  init: RequestInit | undefined,
  asArray: boolean,
): Promise<T | T[]> {
  const token = getToken();
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init?.body && typeof init.body === 'string') {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_PREFIX}${path}`, { ...init, headers });

  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required.');
  }
  if (res.status === 403) {
    throw new ApiError(403, 'Authorisation refused for this tenant or resource.');
  }
  if (res.status === 404) {
    throw new ApiError(404, 'Resource not found.');
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }

  const json = await res.json();
  if (asArray) {
    return (json as unknown[]).map((i) => schema.parse(i));
  }
  return schema.parse(json);
}

// ── Endpoints ───────────────────────────────────────────────────────

export const api = {
  // Auth
  getAuthSession: (): Promise<AuthSession> =>
    requestOne('/auth/session', AuthSessionSchema),

  // Action intents (the ledger + detail)
  listActionIntents: (params?: {
    decision_state?: DecisionState;
    approval_state?: string;
    tenant_id?: string;
    external_reference?: string;
  }): Promise<ActionIntentListItem[]> => {
    const qs = new URLSearchParams();
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v != null) qs.set(k, String(v));
      }
    }
    const suffix = qs.toString() ? `?${qs}` : '';
    return requestMany(`/action-intents${suffix}`, ActionIntentListItemSchema);
  },

  getActionIntent: (id: string): Promise<ActionIntentDetail> =>
    requestOne(`/action-intents/${encodeURIComponent(id)}`, ActionIntentDetailSchema),

  // Audit trace — the Trust Surface gold mine
  getActionTrace: (id: string): Promise<FinanceActionTrace> =>
    requestOne(`/audit/traces/${encodeURIComponent(id)}`, FinanceActionTraceSchema),

  // Receipts
  getReceipt: (id: string): Promise<ReceiptDetail> =>
    requestOne(`/receipts/${encodeURIComponent(id)}`, ReceiptDetailSchema),

  listReceiptsForAction: (actionIntentId: string): Promise<ReceiptDetail[]> => {
    const qs = new URLSearchParams({ action_intent_record_id: actionIntentId });
    return requestMany(`/receipts?${qs}`, ReceiptDetailSchema);
  },

  // Approvals (the review queue)
  listApprovals: (params?: {
    status?: ApprovalRequestStatus;
    tenant_id?: string;
  }): Promise<ApprovalRequest[]> => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.tenant_id) qs.set('tenant_id', params.tenant_id);
    const suffix = qs.toString() ? `?${qs}` : '';
    return requestMany(`/approvals${suffix}`, ApprovalRequestSchema);
  },

  submitApprovalDecision: (
    approvalRequestId: string,
    body: { decision: 'approve' | 'reject'; decision_reason?: string },
  ): Promise<ApprovalRequest> =>
    requestOne(
      `/approvals/${encodeURIComponent(approvalRequestId)}/decisions`,
      ApprovalRequestSchema,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
    ),

  // Transparency / chain verification
  getInclusionProof: (
    logId: string,
    receiptDigest: string,
  ): Promise<InclusionProofResponse> => {
    const qs = new URLSearchParams({ receipt_digest: receiptDigest });
    return requestOne(`/transparency/logs/${encodeURIComponent(logId)}/proofs/inclusion?${qs}`, InclusionProofResponseSchema);
  },
};

export { ApiError };
