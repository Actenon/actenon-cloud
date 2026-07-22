/**
 * SCREEN 2 — THE REVIEW QUEUE
 *
 * Human-in-the-loop approvals. Each row shows the agent, action, amount,
 * requested-at, and the bounded envelope. Approve / Deny posts to the real
 * endpoint and updates optimistically via TanStack Query.
 *
 * Keyboard: j/k to move, a to approve, d to deny.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApprovals, useSubmitApprovalDecision } from '../api/hooks';
import { Card, CardBody, Button, Badge } from '../design/primitives';
import {
  LoadingState,
  EmptyState,
  ErrorState,
} from '../components/TrustComponents';
import { relativeTime } from '../lib/format';
import type { ApprovalRequest } from '../api/schemas';

export function ReviewQueue() {
  const query = useApprovals({ status: 'pending' });
  const mutation = useSubmitApprovalDecision();
  const navigate = useNavigate();
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [reasonText, setReasonText] = useState('');

  const items = useMemo(() => query.data ?? [], [query.data]);

  const act = useCallback(
    (decision: 'approve' | 'reject') => {
      const item = items[selectedIdx];
      if (!item) return;
      mutation.mutate({
        approvalRequestId: item.approval_request_id,
        decision,
        reason: reasonText || undefined,
      });
      setReasonText('');
      setSelectedIdx((i) => Math.max(0, i - 1));
    },
    [items, selectedIdx, mutation, reasonText],
  );

  // Keyboard navigation
  useEffect(() => {
    if (items.length === 0) return;
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'j') {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(items.length - 1, i + 1));
      } else if (e.key === 'k') {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(0, i - 1));
      } else if (e.key === 'a') {
        e.preventDefault();
        act('approve');
      } else if (e.key === 'd') {
        e.preventDefault();
        act('reject');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [items.length, act]);

  if (query.isLoading) return <LoadingState message="Loading review queue" />;
  if (query.error)
    return (
      <ErrorState
        message={query.error instanceof Error ? query.error.message : 'Failed to load approvals.'}
        onRetry={() => query.refetch()}
      />
    );
  if (items.length === 0)
    return (
      <EmptyState
        title="Queue is clear"
        description="No actions are awaiting review. When an agent triggers an approval-required action, it will appear here."
      />
    );

  return (
    <div className="space-y-4">
      {/* Keyboard hint */}
      <div className="flex items-center gap-4 text-2xs text-muted uppercase tracking-wide">
        <span>
          <kbd className="font-mono text-ink bg-surface-2 px-1.5 py-0.5 rounded-xs border border-edge">j</kbd>{' '}
          down
        </span>
        <span>
          <kbd className="font-mono text-ink bg-surface-2 px-1.5 py-0.5 rounded-xs border border-edge">k</kbd>{' '}
          up
        </span>
        <span>
          <kbd className="font-mono text-ink bg-surface-2 px-1.5 py-0.5 rounded-xs border border-edge">a</kbd>{' '}
          approve
        </span>
        <span>
          <kbd className="font-mono text-ink bg-surface-2 px-1.5 py-0.5 rounded-xs border border-edge">d</kbd>{' '}
          deny
        </span>
      </div>

      {items.map((item, idx) => (
        <ReviewRow
          key={item.approval_request_id}
          item={item}
          selected={idx === selectedIdx}
          onSelect={() => setSelectedIdx(idx)}
          onApprove={() => {
            setSelectedIdx(idx);
            act('approve');
          }}
          onReject={() => {
            setSelectedIdx(idx);
            act('reject');
          }}
          onOpenDetail={() => navigate(`/actions/${item.action_intent_record_id}`)}
          reasonText={idx === selectedIdx ? reasonText : ''}
          onReasonChange={idx === selectedIdx ? setReasonText : undefined}
          pending={mutation.isPending && idx === selectedIdx}
        />
      ))}
    </div>
  );
}

interface ReviewRowProps {
  item: ApprovalRequest;
  selected: boolean;
  onSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
  onOpenDetail: () => void;
  reasonText: string;
  onReasonChange?: (v: string) => void;
  pending: boolean;
}

function ReviewRow({
  item,
  selected,
  onSelect,
  onApprove,
  onReject,
  onOpenDetail,
  reasonText,
  onReasonChange,
  pending,
}: ReviewRowProps) {
  return (
    <Card
      className={selected ? 'ring-1 ring-accent' : ''}
      onClick={onSelect}
      tabIndex={0}
      aria-label={`Approval request ${item.approval_request_id}`}
    >
      <CardBody className="space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge tone="pending">PENDING</Badge>
              <span className="font-mono text-sm text-ink">{item.approval_group_key}</span>
              <span className="text-2xs text-muted">{relativeTime(item.created_at)}</span>
            </div>
            <p className="text-sm text-muted">
              Requires {item.required_decision_count} approval{item.required_decision_count > 1 ? 's' : ''}
              {item.expires_at && (
                <> &middot; expires {relativeTime(item.expires_at)}</>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenDetail();
            }}
            className="text-sm text-accent hover:underline font-medium"
          >
            View action &rarr;
          </button>
        </div>

        {/* Action summary */}
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <div>
            <dt className="text-2xs uppercase tracking-wide text-muted">Action intent</dt>
            <dd className="font-mono text-ink">{item.action_intent_record_id}</dd>
          </div>
          <div>
            <dt className="text-2xs uppercase tracking-wide text-muted">Tenant</dt>
            <dd className="font-mono text-ink">{item.tenant_id}</dd>
          </div>
          <div>
            <dt className="text-2xs uppercase tracking-wide text-muted">Group</dt>
            <dd className="font-mono text-ink">{item.approval_group_key}</dd>
          </div>
          <div>
            <dt className="text-2xs uppercase tracking-wide text-muted">Roles</dt>
            <dd className="font-mono text-2xs text-ink">{item.eligible_role_ids.join(', ') || '—'}</dd>
          </div>
        </dl>

        {/* Reason input (only on selected row) */}
        {selected && onReasonChange && (
          <div className="pt-2 border-t border-edge">
            <label
              htmlFor={`reason-${item.approval_request_id}`}
              className="text-2xs font-semibold uppercase tracking-wide text-muted block mb-1"
            >
              Reason (optional)
            </label>
            <input
              id={`reason-${item.approval_request_id}`}
              type="text"
              value={reasonText}
              onChange={(e) => onReasonChange(e.target.value)}
              placeholder="Add a reason for the decision"
              className="w-full h-8 px-3 text-sm bg-surface-2 border border-edge rounded-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 pt-1">
          <Button
            variant="allow"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onApprove();
            }}
            disabled={pending}
          >
            Approve
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onReject();
            }}
            disabled={pending}
          >
            Deny
          </Button>
          {pending && (
            <span className="text-2xs text-muted">Submitting&hellip;</span>
          )}
        </div>
      </CardBody>
    </Card>
  );
}
