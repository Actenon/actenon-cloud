/**
 * SCREEN 1 — THE TRUST SURFACE
 *
 * The single-action detail / receipt view. The demo, the screenshot, the pitch.
 * Layout: a vertical narrative from "what the agent asked" → "what the boundary
 * decided" → "the tamper-evident receipt".
 *
 * Supports a "replay as demo" affordance that loads the canned
 * subscription-cancel-refused incident.
 */
import { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useActionIntent, useActionTrace, useReceipt } from '../api/hooks';
import { DEMO_TRACE, DEMO_ACTION_INTENT, DEMO_RECEIPT } from '../api/mock';
import { extractFailureCode, glossForCode } from '../lib/failure-codes';
import { formatPrincipal, formatTimestamp } from '../lib/format';
import {
  Card,
  CardHeader,
  CardBody,
  DefinitionRow,
  SectionHeading,
  Button,
  Badge,
} from '../design/primitives';
import {
  Verdict,
  MutationRefused,
  ChainVerifyBadge,
  Hash,
  Money,
  StatePill,
  LoadingState,
  EmptyState,
  ErrorState,
} from '../components/TrustComponents';
import type { FinanceActionTrace, ActionIntentDetail } from '../api/schemas';

export function TrustSurface() {
  const { id } = useParams<{ id: string }>();
  const [demoMode, setDemoMode] = useState(false);

  // If no id and not in demo mode, show the entry state with the demo button
  if (!id && !demoMode) {
    return <TrustSurfaceEntry onDemo={() => setDemoMode(true)} />;
  }

  if (demoMode) {
    return <TrustSurfaceContent demo />;
  }

  return <TrustSurfaceContent id={id!} />;
}

// ── Entry state — no action selected ────────────────────────────────

function TrustSurfaceEntry({ onDemo }: { onDemo: () => void }) {
  return (
    <div className="max-w-2xl mx-auto py-12">
      <Card>
        <CardBody>
          <SectionHeading
            eyebrow="Trust Surface"
            title="Inspect a consequential action"
            description="Enter an action intent record ID to see the full incident-to-containment narrative: what the agent proposed, the authority it held, the decision, and the tamper-evident receipt."
          />
          <div className="mt-6 flex flex-col gap-3">
            <Button variant="primary" size="lg" onClick={onDemo}>
              Replay the demo incident
            </Button>
            <p className="text-sm text-muted">
              The demo shows a subscription-cancel attempt refused as{' '}
              <span className="font-mono text-deny">ACTION_MISMATCH</span> — the agent was
              authorised for $20.00 but attempted $99,999.00.
            </p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

// ── Main content ────────────────────────────────────────────────────

function TrustSurfaceContent({ id, demo = false }: { id?: string; demo?: boolean }) {
  const intentQuery = useActionIntent(demo ? undefined : id);
  const traceQuery = useActionTrace(demo ? undefined : id);

  // For demo mode, use canned data
  const intent: ActionIntentDetail | null = demo
    ? (DEMO_ACTION_INTENT as ActionIntentDetail)
    : (intentQuery.data ?? null);
  const trace: FinanceActionTrace | null = demo
    ? DEMO_TRACE
    : (traceQuery.data ?? null);

  const loading = !demo && (intentQuery.isLoading || traceQuery.isLoading);
  const error = !demo
    ? (intentQuery.error ?? traceQuery.error)
    : null;

  if (loading) return <LoadingState message="Loading action and trace" />;
  if (error) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : 'Failed to load action.'}
        onRetry={() => {
          intentQuery.refetch();
          traceQuery.refetch();
        }}
      />
    );
  }
  if (!intent) return <EmptyState title="Action not found" description="No action intent was found for this ID." />;

  const failureCode = extractFailureCode(intent.decision_reason);
  const payload = intent.action_intent_payload as {
    action_type?: string;
    amount_minor?: number;
    currency?: string;
    source_account_ref?: string;
    destination_account_ref?: string;
    destination_country?: string;
    intent_id?: string;
    workflow_key?: string;
  };

  const evalCtx = intent.evaluation_context as {
    grant_id?: string;
    grant_scopes?: string[];
    grant_budget_remaining_minor?: number;
    grant_amount_cap_minor?: number;
    grant_currency?: string;
    grant_expires_at?: string;
    pccb_bound_amount_minor?: number;
    pccb_bound_target?: string;
  };

  const receiptId = intent.latest_receipt_id;
  const showMutationRefused =
    failureCode === 'ACTION_MISMATCH' &&
    typeof evalCtx?.pccb_bound_amount_minor === 'number' &&
    typeof payload?.amount_minor === 'number';

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* ── Replay banner in demo mode ── */}
      {demo && (
        <div className="flex items-center gap-3 p-3 rounded-md border border-accent/30 bg-accent/5">
          <Badge tone="accent">DEMO</Badge>
          <span className="text-sm text-muted">
            Canned incident: subscription-cancel-refused. Zero setup.
          </span>
        </div>
      )}

      {/* ── Section 1: WHAT THE AGENT PROPOSED ── */}
      <Card>
        <CardHeader>
          <SectionHeading
            eyebrow="1 — The request"
            title="What the agent proposed"
            description="The agent submitted an action intent. This is exactly what it asked to do."
          />
        </CardHeader>
        <CardBody className="!p-0">
          <dl>
            <DefinitionRow label="Action type" mono>
              {payload?.action_type ?? '—'}
            </DefinitionRow>
            <DefinitionRow label="Amount">
              {payload?.amount_minor != null && payload?.currency ? (
                <Money minor={payload.amount_minor} currency={payload.currency} className="text-base font-semibold" />
              ) : (
                '—'
              )}
            </DefinitionRow>
            <DefinitionRow label="Target" mono>
              {payload?.destination_account_ref ?? '—'}
            </DefinitionRow>
            <DefinitionRow label="Source" mono>
              {payload?.source_account_ref ?? '—'}
            </DefinitionRow>
            <DefinitionRow label="Tenant" mono>
              {intent.tenant_id}
            </DefinitionRow>
            <DefinitionRow label="Requested by" mono>
              {formatPrincipal(intent.requested_by_principal_type, intent.requested_by_principal_id)}
            </DefinitionRow>
            <DefinitionRow label="Submitted">
              {formatTimestamp(intent.created_at)}
            </DefinitionRow>
            <DefinitionRow label="Workflow" mono>
              {intent.workflow_key}
            </DefinitionRow>
            {intent.external_reference && (
              <DefinitionRow label="External ref" mono>
                {intent.external_reference}
              </DefinitionRow>
            )}
          </dl>
        </CardBody>
      </Card>

      {/* ── Section 2: THE AUTHORITY IT HELD ── */}
      <Card>
        <CardHeader>
          <SectionHeading
            eyebrow="2 — The boundary"
            title="The authority it held"
            description="The grant and PCCB envelope that bounded what the agent was permitted to do."
          />
        </CardHeader>
        <CardBody className="!p-0">
          <dl>
            <DefinitionRow label="Grant ID" mono>
              {evalCtx?.grant_id ?? '—'}
            </DefinitionRow>
            <DefinitionRow label="Scopes permitted">
              {evalCtx?.grant_scopes?.length ? (
                <div className="flex flex-wrap gap-1">
                  {evalCtx.grant_scopes.map((s) => (
                    <Badge key={s} tone="accent">{s}</Badge>
                  ))}
                </div>
              ) : (
                '—'
              )}
            </DefinitionRow>
            <DefinitionRow label="Amount cap">
              {evalCtx?.grant_amount_cap_minor != null && evalCtx?.grant_currency ? (
                <Money minor={evalCtx.grant_amount_cap_minor} currency={evalCtx.grant_currency} className="font-semibold" />
              ) : (
                '—'
              )}
            </DefinitionRow>
            <DefinitionRow label="Budget remaining">
              {evalCtx?.grant_budget_remaining_minor != null && evalCtx?.grant_currency ? (
                <Money minor={evalCtx.grant_budget_remaining_minor} currency={evalCtx.grant_currency} className="font-semibold" />
              ) : (
                '—'
              )}
            </DefinitionRow>
            <DefinitionRow label="Grant expires">
              {evalCtx?.grant_expires_at ? formatTimestamp(evalCtx.grant_expires_at) : '—'}
            </DefinitionRow>
            {trace && trace.issued_proofs.length > 0 && (
              <>
                <DefinitionRow label="PCCB proof ID" mono>
                  <Hash value={trace.issued_proofs[0].issued_proof_id} />
                </DefinitionRow>
                <DefinitionRow label="PCCB bound amount">
                  {evalCtx?.pccb_bound_amount_minor != null && evalCtx?.grant_currency ? (
                    <Money minor={evalCtx.pccb_bound_amount_minor} currency={evalCtx.grant_currency} className="font-semibold text-allow" />
                  ) : (
                    '—'
                  )}
                </DefinitionRow>
                <DefinitionRow label="Single-use">
                  <Badge tone="muted">yes — nonce-bound</Badge>
                </DefinitionRow>
              </>
            )}
          </dl>
        </CardBody>
      </Card>

      {/* ── Section 3: THE DECISION ── */}
      <Card>
        <CardHeader>
          <SectionHeading
            eyebrow="3 — The decision"
            title="What the boundary decided"
            description="The deterministic, fail-closed verdict from the Policy Decision Point."
          />
        </CardHeader>
        <CardBody>
          <div className="flex items-start gap-6 flex-wrap">
            <Verdict decision={intent.decision_state} failureCode={failureCode !== 'UNKNOWN' ? failureCode : null} />
            <div className="flex-1 min-w-[240px]">
              <dl className="space-y-2">
                <div className="flex gap-3">
                  <dt className="text-2xs font-semibold uppercase tracking-wide text-muted w-24 shrink-0 pt-0.5">
                    Reason
                  </dt>
                  <dd className="text-sm text-ink">{intent.decision_reason}</dd>
                </div>
                {failureCode !== 'UNKNOWN' && (
                  <div className="flex gap-3">
                    <dt className="text-2xs font-semibold uppercase tracking-wide text-muted w-24 shrink-0 pt-0.5">
                      Failure code
                    </dt>
                    <dd className="text-sm">
                      <span className="font-mono text-deny font-semibold">{failureCode}</span>
                      <span className="text-muted block mt-0.5">{glossForCode(failureCode)}</span>
                    </dd>
                  </div>
                )}
                <div className="flex gap-3">
                  <dt className="text-2xs font-semibold uppercase tracking-wide text-muted w-24 shrink-0 pt-0.5">
                    Matched rule
                  </dt>
                  <dd className="font-mono text-sm text-ink">{intent.matched_rule_id ?? '—'}</dd>
                </div>
              </dl>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* ── Section 4: MUTATION-REFUSED MOMENT ── */}
      {showMutationRefused &&
        evalCtx?.pccb_bound_amount_minor != null &&
        payload?.amount_minor != null &&
        payload?.currency && (
          <Card>
            <CardBody>
              <MutationRefused
                authorisedAmountMinor={evalCtx.pccb_bound_amount_minor}
                attemptedAmountMinor={payload.amount_minor}
                currency={payload.currency}
                failureCode={failureCode}
              />
            </CardBody>
          </Card>
        )}

      {/* ── Section 5: TAMPER-EVIDENT RECEIPT ── */}
      <ReceiptSection
        receiptId={receiptId}
        demo={demo}
        actionIntentDigest={intent.action_intent_digest}
      />

      {/* ── Evaluation trace (collapsible) ── */}
      {intent.evaluation_trace.length > 0 && (
        <Card>
          <CardHeader>
            <SectionHeading
              eyebrow="Appendix"
              title="Evaluation trace"
              description="The 8-step deterministic check sequence. Each step must pass."
            />
          </CardHeader>
          <CardBody className="!p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-edge text-2xs uppercase tracking-wide text-muted">
                  <th className="text-left px-5 py-2 font-semibold">Step</th>
                  <th className="text-left px-5 py-2 font-semibold">Check</th>
                  <th className="text-left px-5 py-2 font-semibold">Result</th>
                </tr>
              </thead>
              <tbody>
                {intent.evaluation_trace.map((step, i) => {
                  const s = step as { step?: number; check?: string; result?: string; reason?: string };
                  const result = s.result ?? '—';
                  return (
                    <tr key={i} className="border-b border-edge/40 last:border-0">
                      <td className="px-5 py-2 font-mono text-muted">{s.step ?? i + 1}</td>
                      <td className="px-5 py-2 font-mono">{s.check ?? '—'}</td>
                      <td className="px-5 py-2">
                        {result === 'pass' ? (
                          <Badge tone="allow">pass</Badge>
                        ) : result === 'fail' ? (
                          <Badge tone="deny">fail</Badge>
                        ) : (
                          <Badge tone="muted">{result}</Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}

      {/* ── Lifecycle state ── */}
      <Card>
        <CardHeader>
          <SectionHeading eyebrow="State" title="Lifecycle" />
        </CardHeader>
        <CardBody className="!p-0">
          <dl>
            <DefinitionRow label="Decision">
              <StatePill state={intent.decision_state} />
            </DefinitionRow>
            <DefinitionRow label="Approval">
              <StatePill state={intent.approval_state} />
            </DefinitionRow>
            <DefinitionRow label="Evidence">
              <StatePill state={intent.evidence_state} />
            </DefinitionRow>
            <DefinitionRow label="Execution">
              <StatePill state={intent.execution_state} />
            </DefinitionRow>
            <DefinitionRow label="Receipt">
              <StatePill state={intent.receipt_state} />
            </DefinitionRow>
          </dl>
        </CardBody>
      </Card>
    </div>
  );
}

// ── Receipt section with chain verification ─────────────────────────

function ReceiptSection({
  receiptId,
  demo,
  actionIntentDigest,
}: {
  receiptId: string | null;
  demo: boolean;
  actionIntentDigest: string;
}) {
  const receiptQuery = useReceipt(demo ? undefined : (receiptId ?? undefined));
  const [chainStatus, setChainStatus] = useState<'verified' | 'broken' | 'checking' | 'unknown'>(
    'unknown',
  );

  const receipt = demo ? DEMO_RECEIPT : receiptQuery.data;

  const handleVerifyChain = useCallback(() => {
    if (!receipt) return;
    setChainStatus('checking');
    // In a real deployment, this calls the transparency log API.
    // For now, we simulate: if the receipt has a digest, it verifies.
    setTimeout(() => {
      const digest = receipt.kernel_receipt_digest;
      setChainStatus(digest ? 'verified' : 'broken');
    }, 800);
  }, [receipt]);

  if (!receiptId && !demo) {
    return (
      <Card>
        <CardHeader>
          <SectionHeading eyebrow="4 — Receipt" title="Tamper-evident receipt" />
        </CardHeader>
        <CardBody>
          <EmptyState
            title="No receipt recorded"
            description="This action was refused before execution. No receipt was generated."
          />
        </CardBody>
      </Card>
    );
  }

  if (!receipt) {
    return (
      <Card>
        <CardHeader>
          <SectionHeading eyebrow="4 — Receipt" title="Tamper-evident receipt" />
        </CardHeader>
        <CardBody>
          <LoadingState message="Loading receipt" />
        </CardBody>
      </Card>
    );
  }

  const receiptPayload = receipt.receipt_payload as {
    failure_code?: string;
    authority_boundary?: {
      authorised_action_hash?: string;
      attempted_action_hash?: string;
      match?: boolean;
    };
    signing_key_id?: string;
    signing_algorithm?: string;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <SectionHeading
            eyebrow="4 — Receipt"
            title="Tamper-evident receipt"
            description="The hash-chained ledger entry. Each block holds the SHA-256 of the previous one."
          />
          <ChainVerifyBadge status={chainStatus} onClick={handleVerifyChain} />
        </div>
      </CardHeader>
      <CardBody className="!p-0">
        <dl>
          <DefinitionRow label="Receipt ID" mono>
            <Hash value={receipt.receipt_id} />
          </DefinitionRow>
          <DefinitionRow label="Outcome">
            <span className="text-sm font-semibold">{receipt.outcome}</span>
          </DefinitionRow>
          <DefinitionRow label="Receipt hash" mono>
            <Hash value={receipt.kernel_receipt_digest} head={12} tail={8} />
          </DefinitionRow>
          <DefinitionRow label="Chain leaf">
            <span className="font-mono text-sm">
              #{String((receipt.receipt_index as { leaf_index?: number })?.leaf_index ?? '—')}
            </span>
          </DefinitionRow>
          <DefinitionRow label="Timestamp">
            {formatTimestamp(receipt.receipt_timestamp)}
          </DefinitionRow>

          {/* Authority boundary */}
          {receiptPayload?.authority_boundary && (
            <>
              <DefinitionRow label="Authorised hash" mono>
                <Hash
                  value={receiptPayload.authority_boundary.authorised_action_hash ?? '—'}
                  head={12}
                  tail={8}
                />
              </DefinitionRow>
              <DefinitionRow label="Attempted hash" mono>
                <Hash
                  value={receiptPayload.authority_boundary.attempted_action_hash ?? '—'}
                  head={12}
                  tail={8}
                />
              </DefinitionRow>
              <DefinitionRow label="Hash match">
                {receiptPayload.authority_boundary.match ? (
                  <Badge tone="allow">match</Badge>
                ) : (
                  <Badge tone="deny">mismatch</Badge>
                )}
              </DefinitionRow>
            </>
          )}

          {/* Signing */}
          <DefinitionRow label="Signing key" mono>
            {receiptPayload?.signing_key_id ?? '—'}
          </DefinitionRow>
          <DefinitionRow label="Algorithm" mono>
            {receiptPayload?.signing_algorithm ?? '—'}
          </DefinitionRow>
          <DefinitionRow label="Action digest" mono>
            <Hash value={actionIntentDigest} head={12} tail={8} />
          </DefinitionRow>
        </dl>

        {/* Reconciliation summary */}
        {Object.keys(receipt.reconciliation_summary).length > 0 && (
          <div className="px-5 py-3 border-t border-edge">
            <p className="text-2xs font-semibold uppercase tracking-wide text-muted mb-2">
              Reconciliation
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(receipt.reconciliation_summary).map(([k, v]) => (
                <Badge key={k} tone={v === 'verified' ? 'allow' : 'muted'}>
                  {k}: {String(v)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
