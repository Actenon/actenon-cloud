/**
 * SCREEN 3 — THE ACTION LEDGER
 *
 * A dense, legible, sortable table of recent decisions with the structured
 * failure_code as a first-class, filterable, color-coded column.
 * Sticky header. Click-through to the Trust Surface.
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useActionIntents } from '../api/hooks';
import { Card, Badge } from '../design/primitives';
import {
  LoadingState,
  EmptyState,
  ErrorState,
  Money,
  StatePill,
} from '../components/TrustComponents';
import { extractFailureCode } from '../lib/failure-codes';
import { relativeTime, formatPrincipal } from '../lib/format';
import { ALL_FAILURE_CODES, type FailureCode } from '../lib/failure-codes';
import type { DecisionState } from '../api/schemas';

const DECISION_FILTERS: { label: string; value: DecisionState | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Allow', value: 'allow' },
  { label: 'Refused', value: 'deny' },
  { label: 'Approval required', value: 'approval_required' },
];

export function ActionLedger() {
  const [decisionFilter, setDecisionFilter] = useState<DecisionState | 'all'>('all');
  const [codeFilter, setCodeFilter] = useState<FailureCode | 'all'>('all');
  const navigate = useNavigate();

  const query = useActionIntents(
    decisionFilter !== 'all' ? { decision_state: decisionFilter } : undefined,
  );

  const items = query.data ?? [];

  // Client-side filter by failure code (extracted from decision_reason)
  const filtered = useMemo(() => {
    if (codeFilter === 'all') return items;
    return items.filter((item) => extractFailureCode(item.decision_reason) === codeFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.data, codeFilter]);

  if (query.isLoading) return <LoadingState message="Loading action ledger" />;
  if (query.error)
    return (
      <ErrorState
        message={query.error instanceof Error ? query.error.message : 'Failed to load actions.'}
        onRetry={() => query.refetch()}
      />
    );

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1">
          <span className="text-2xs font-semibold uppercase tracking-wide text-muted mr-2">
            Decision
          </span>
          {DECISION_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setDecisionFilter(f.value)}
              className={`px-2.5 py-1 text-2xs font-semibold uppercase tracking-wide rounded-xs border transition-colors ${
                decisionFilter === f.value
                  ? 'bg-accent/15 text-accent border-accent/40'
                  : 'bg-surface-2 text-muted border-edge hover:text-ink'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <label htmlFor="code-filter" className="text-2xs font-semibold uppercase tracking-wide text-muted mr-2">
            Failure code
          </label>
          <select
            id="code-filter"
            value={codeFilter}
            onChange={(e) => setCodeFilter(e.target.value as FailureCode | 'all')}
            className="h-7 px-2 text-2xs bg-surface-2 border border-edge rounded-xs text-ink focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="all">All</option>
            {ALL_FAILURE_CODES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <span className="text-2xs text-muted ml-auto">
          {filtered.length} action{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No actions match"
          description="No actions match the current filters. Try widening the selection."
        />
      ) : (
        <Card padded={false} className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-2 border-b border-edge">
                <tr className="text-2xs uppercase tracking-wide text-muted">
                  <th className="text-left px-4 py-2 font-semibold">When</th>
                  <th className="text-left px-4 py-2 font-semibold">Agent</th>
                  <th className="text-left px-4 py-2 font-semibold">Action</th>
                  <th className="text-right px-4 py-2 font-semibold">Amount</th>
                  <th className="text-left px-4 py-2 font-semibold">Decision</th>
                  <th className="text-left px-4 py-2 font-semibold">Failure code</th>
                  <th className="text-left px-4 py-2 font-semibold">Tenant</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const code = extractFailureCode(item.decision_reason);
                  return (
                    <tr
                      key={item.action_intent_record_id}
                      onClick={() => navigate(`/actions/${item.action_intent_record_id}`)}
                      className="border-b border-edge/40 last:border-0 cursor-pointer hover:bg-surface-2 transition-colors"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') navigate(`/actions/${item.action_intent_record_id}`);
                      }}
                    >
                      <td className="px-4 py-2 text-muted whitespace-nowrap">
                        {relativeTime(item.created_at)}
                      </td>
                      <td className="px-4 py-2 font-mono text-2xs">
                        {formatPrincipal(item.requested_by_principal_type, item.requested_by_principal_id)}
                      </td>
                      <td className="px-4 py-2 font-mono text-2xs">
                        {item.workflow_key}
                      </td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums whitespace-nowrap">
                        {item.amount_minor != null && item.currency ? (
                          <Money minor={item.amount_minor} currency={item.currency} />
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <StatePill state={item.decision_state} />
                      </td>
                      <td className="px-4 py-2">
                        {code !== 'UNKNOWN' ? (
                          <Badge tone="deny">{code}</Badge>
                        ) : (
                          <span className="text-muted text-2xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2 font-mono text-2xs text-muted">
                        {item.tenant_id}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
