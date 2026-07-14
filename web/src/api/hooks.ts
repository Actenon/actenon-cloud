/**
 * TanStack Query hooks for each API endpoint.
 * Each hook handles loading, error, and empty states via the components layer.
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from '@tanstack/react-query';
import { api } from './client';
import type { ApprovalRequestStatus, DecisionState } from './schemas';

// ── Query keys ──────────────────────────────────────────────────────

export const qk = {
  authSession: ['auth-session'] as const,
  actionIntents: (params?: Record<string, string>) => ['action-intents', params ?? {}] as const,
  actionIntent: (id: string) => ['action-intent', id] as const,
  actionTrace: (id: string) => ['action-trace', id] as const,
  receipt: (id: string) => ['receipt', id] as const,
  receiptsForAction: (id: string) => ['receipts-for-action', id] as const,
  approvals: (params?: Record<string, string>) => ['approvals', params ?? {}] as const,
};

// ── Auth ────────────────────────────────────────────────────────────

export function useAuthSession() {
  return useQuery({
    queryKey: qk.authSession,
    queryFn: () => api.getAuthSession(),
    retry: false,
    staleTime: 60_000,
  });
}

// ── Action intents (ledger) ─────────────────────────────────────────

export function useActionIntents(params?: {
  decision_state?: DecisionState;
  tenant_id?: string;
}) {
  const flat: Record<string, string> = {};
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v != null) flat[k] = String(v);
    }
  }
  return useQuery({
    queryKey: qk.actionIntents(flat),
    queryFn: () => api.listActionIntents(params),
    staleTime: 10_000,
    placeholderData: keepPreviousData,
  });
}

// ── Action intent detail ────────────────────────────────────────────

export function useActionIntent(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.actionIntent(id) : ['action-intent', 'none'],
    queryFn: () => {
      if (!id) throw new Error('No action intent id');
      return api.getActionIntent(id);
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

// ── Audit trace (Trust Surface) ─────────────────────────────────────

export function useActionTrace(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.actionTrace(id) : ['action-trace', 'none'],
    queryFn: () => {
      if (!id) throw new Error('No action intent id');
      return api.getActionTrace(id);
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

// ── Receipt ─────────────────────────────────────────────────────────

export function useReceipt(id: string | undefined) {
  return useQuery({
    queryKey: id ? qk.receipt(id) : ['receipt', 'none'],
    queryFn: () => {
      if (!id) throw new Error('No receipt id');
      return api.getReceipt(id);
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

// ── Approvals (review queue) ────────────────────────────────────────

export function useApprovals(params?: { status?: ApprovalRequestStatus }) {
  const flat: Record<string, string> = {};
  if (params?.status) flat.status = params.status;
  return useQuery({
    queryKey: qk.approvals(flat),
    queryFn: () => api.listApprovals(params),
    staleTime: 5_000,
    refetchInterval: 15_000,
  });
}

export function useSubmitApprovalDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { approvalRequestId: string; decision: 'approve' | 'reject'; reason?: string }) =>
      api.submitApprovalDecision(args.approvalRequestId, {
        decision: args.decision,
        decision_reason: args.reason,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] });
      qc.invalidateQueries({ queryKey: ['action-intents'] });
    },
  });
}

// ── Chain verification ──────────────────────────────────────────────

export function useInclusionProof(logId: string, receiptDigest: string | null) {
  return useQuery({
    queryKey: ['inclusion-proof', logId, receiptDigest],
    queryFn: () => {
      if (!receiptDigest) throw new Error('No receipt digest');
      return api.getInclusionProof(logId, receiptDigest);
    },
    enabled: !!receiptDigest,
    staleTime: Infinity,
  });
}
