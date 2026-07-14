/**
 * Specialised components for the Trust Surface and screens.
 */
import { useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { cn } from '../lib/cn';
import { Badge, Spinner } from '../design/primitives';
import { formatMoney, diffMoney } from '../lib/money';
import { truncateHash, copyToClipboard, formatTimestamp } from '../lib/format';
import type { DecisionState, ApprovalState, ExecutionState, ReceiptState } from '../api/schemas';

// ── Verdict — the large, unambiguous ALLOW / DENY / APPROVAL_REQUIRED ─

interface VerdictProps {
  decision: DecisionState;
  failureCode?: string | null;
}

const verdictConfig: Record<
  DecisionState,
  { label: string; tone: 'allow' | 'deny' | 'pending'; className: string }
> = {
  allow: { label: 'ALLOW', tone: 'allow', className: 'verdict-allow' },
  deny: { label: 'REFUSED', tone: 'deny', className: 'verdict-deny' },
  approval_required: { label: 'APPROVAL REQUIRED', tone: 'pending', className: 'verdict-pending' },
  needs_evidence: { label: 'EVIDENCE REQUIRED', tone: 'pending', className: 'verdict-pending' },
  structurally_non_executable: { label: 'NOT EXECUTABLE', tone: 'deny', className: 'verdict-deny' },
};

export function Verdict({ decision, failureCode }: VerdictProps) {
  const config = verdictConfig[decision];
  return (
    <div
      className={cn(
        'inline-flex flex-col gap-1 px-6 py-4 rounded-lg border-2',
        config.className,
      )}
      role="status"
      aria-live="polite"
    >
      <span className="text-2xs font-semibold uppercase tracking-widest opacity-70">
        Decision
      </span>
      <span className="text-3xl font-bold tracking-tight">{config.label}</span>
      {failureCode && (
        <span className="font-mono text-sm font-semibold mt-1 opacity-90">
          {failureCode}
        </span>
      )}
    </div>
  );
}

// ── MutationRefused — the visceral diff row ──────────────────────────

interface MutationRefusedProps {
  authorisedAmountMinor: number;
  attemptedAmountMinor: number;
  currency: string;
  failureCode: string;
}

export function MutationRefused({
  authorisedAmountMinor,
  attemptedAmountMinor,
  currency,
  failureCode,
}: MutationRefusedProps) {
  const delta = diffMoney(authorisedAmountMinor, attemptedAmountMinor, currency);
  return (
    <div
      className="rounded-md border border-deny/30 bg-deny/5 p-4"
      role="alert"
      aria-label="Mutation refused: the attempted action did not match the authorised action"
    >
      <div className="flex items-center gap-2 mb-3">
        <svg width="16" height="16" viewBox="0 0 16 16" className="text-deny" aria-hidden="true">
          <path
            d="M8 1L1 14h14L8 1zm0 4v5M8 11v1"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
        <span className="text-sm font-semibold text-deny">
          Mutation refused before execution
        </span>
      </div>
      <div className="flex items-center gap-3 font-mono text-sm flex-wrap">
        <span className="text-muted">authorised</span>
        <span className="text-allow font-semibold">
          {formatMoney(authorisedAmountMinor, currency)}
        </span>
        <span className="text-muted" aria-hidden="true">
          &rarr;
        </span>
        <span className="text-muted">attempted</span>
        <span className="text-deny font-semibold line-through decoration-deny/60">
          {formatMoney(attemptedAmountMinor, currency)}
        </span>
        <span className="text-muted" aria-hidden="true">
          &rarr;
        </span>
        <Badge tone="deny">REFUSED</Badge>
        <span className="font-mono text-2xs text-deny font-semibold">{failureCode}</span>
        <span className="text-muted text-2xs ml-auto">{delta}</span>
      </div>
    </div>
  );
}

// ── ChainVerifyBadge — green tick / red broken / preview (honest) ───
//
// The 'verified' state is ONLY shown after a real call to the
// transparency-log inclusion-proof API returns a valid proof.
// The 'preview' state is shown when no backend is available (demo mode)
// — it does NOT claim verification, because that would be trust theatre.

interface ChainVerifyBadgeProps {
  status: 'verified' | 'broken' | 'checking' | 'unknown' | 'preview';
  onClick?: () => void;
}

export function ChainVerifyBadge({ status, onClick }: ChainVerifyBadgeProps) {
  if (status === 'checking') {
    return (
      <span className="inline-flex items-center gap-2 text-sm text-muted">
        <Spinner className="h-3 w-3" /> Verifying chain&hellip;
      </span>
    );
  }

  if (status === 'preview') {
    return (
      <span
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-2xs font-semibold uppercase tracking-wide rounded-xs border bg-surface-2 text-muted border-edge"
        title="Verification runs at the kernel edge against the live transparency log. No backend is connected in this preview."
      >
        <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true">
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none" />
          <path d="M8 5v3M8 10.5v1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        Preview &mdash; runs at kernel edge
      </span>
    );
  }

  const config = {
    verified: {
      tone: 'allow' as const,
      label: 'CHAIN VERIFIED',
      icon: (
        <path d="M3 8l3 3 7-7" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      ),
    },
    broken: {
      tone: 'deny' as const,
      label: 'CHAIN BROKEN',
      icon: (
        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
      ),
    },
    unknown: {
      tone: 'muted' as const,
      label: 'NOT VERIFIED',
      icon: (
        <path d="M8 2v6M8 12v2" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
      ),
    },
  }[status];

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 text-2xs font-semibold uppercase tracking-wide rounded-xs border transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
        status === 'verified' && 'bg-allow/10 text-allow border-allow/30 hover:bg-allow/20',
        status === 'broken' && 'bg-deny/10 text-deny border-deny/30 hover:bg-deny/20',
        status === 'unknown' && 'bg-surface-2 text-muted border-edge hover:bg-edge',
      )}
      aria-label={`${config.label}. Click to verify.`}
    >
      <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true">
        {config.icon}
      </svg>
      {config.label}
    </button>
  );
}

// ── Hash — monospace hash with copy ─────────────────────────────────

interface HashProps {
  value: string;
  head?: number;
  tail?: number;
  copyable?: boolean;
  label?: string;
}

export function Hash({ value, head = 8, tail = 6, copyable = true, label }: HashProps) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(async () => {
    const ok = await copyToClipboard(value);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  }, [value]);

  const display = label ?? truncateHash(value, head, tail);

  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-sm">
      <span title={value} className="text-ink">
        {display}
      </span>
      {copyable && (
        <button
          type="button"
          onClick={handleCopy}
          className="text-muted hover:text-accent transition-colors"
          aria-label="Copy full hash"
        >
          {copied ? (
            <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 8l3 3 7-7" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true">
              <rect x="4" y="4" width="8" height="8" rx="1" stroke="currentColor" strokeWidth="1.5" fill="none" />
              <path d="M6 4V3a1 1 0 011-1h5a1 1 0 011 1v5a1 1 0 01-1 1h-1" stroke="currentColor" strokeWidth="1.5" fill="none" />
            </svg>
          )}
        </button>
      )}
    </span>
  );
}

// ── Money — monospace money display ─────────────────────────────────

interface MoneyProps {
  minor: number;
  currency: string;
  className?: string;
}

export function Money({ minor, currency, className }: MoneyProps) {
  return (
    <span className={cn('font-mono tabular-nums', className)}>
      {formatMoney(minor, currency)}
    </span>
  );
}

// ── StatePill — lifecycle state indicator ───────────────────────────

type AnyState = DecisionState | ApprovalState | ExecutionState | ReceiptState | string;

const stateTones: Record<string, 'allow' | 'deny' | 'pending' | 'neutral'> = {
  allow: 'allow',
  deny: 'deny',
  approval_required: 'pending',
  needs_evidence: 'pending',
  structurally_non_executable: 'deny',
  not_required: 'neutral',
  not_started: 'neutral',
  pending: 'pending',
  satisfied: 'allow',
  rejected: 'deny',
  expired: 'deny',
  canceled: 'neutral',
  none: 'neutral',
  received: 'allow',
  indexed: 'allow',
  reconciled: 'allow',
  superseded: 'neutral',
  capability_held: 'pending',
  capability_released: 'allow',
  result_observed: 'allow',
  failure_observed: 'deny',
  revoked: 'deny',
  quarantined: 'deny',
};

export function StatePill({ state, label }: { state: AnyState; label?: string }) {
  const tone = stateTones[state] ?? 'neutral';
  return (
    <Badge tone={tone}>
      {label ?? String(state).replace(/_/g, ' ')}
    </Badge>
  );
}

// ── Loading / Empty / Error states ──────────────────────────────────

export function LoadingState({ message = 'Loading' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-muted" role="status" aria-live="polite">
      <Spinner />
      <span className="text-sm">{message}&hellip;</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <svg width="40" height="40" viewBox="0 0 40 40" className="text-edge-strong mb-4" aria-hidden="true">
        <rect x="8" y="8" width="24" height="24" rx="3" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <path d="M14 20h12M14 24h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <h3 className="text-sm font-semibold text-ink mb-1">{title}</h3>
      <p className="text-sm text-muted max-w-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      className="flex flex-col items-center justify-center py-12 px-6 text-center"
      role="alert"
    >
      <svg width="32" height="32" viewBox="0 0 32 32" className="text-deny mb-3" aria-hidden="true">
        <circle cx="16" cy="16" r="13" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <path d="M16 9v8M16 21v1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <p className="text-sm text-ink font-medium mb-1">Something went wrong</p>
      <p className="text-sm text-muted max-w-sm">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 text-sm text-accent hover:underline font-medium"
        >
          Try again
        </button>
      )}
    </div>
  );
}

// ── Timestamp ───────────────────────────────────────────────────────

export function Timestamp({ iso, relative = false }: { iso: string; relative?: boolean }) {
  const text = relative ? formatTimestamp(iso) : formatTimestamp(iso);
  return (
    <time dateTime={iso} className="text-sm text-muted" title={iso}>
      {text}
    </time>
  );
}
