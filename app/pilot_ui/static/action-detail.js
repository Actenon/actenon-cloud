import {
  deriveInvoiceReference,
  deriveLifecycleStage,
  deriveOperatorStatus,
  deriveOutcome,
  derivePayeeReference,
  deriveReceiptAvailability,
  deriveReviewDisposition,
  currentPrincipal,
  downloadEvidenceContent,
  downloadTraceExport,
  escapeHtml,
  fetchJson,
  formatDateTime,
  formatLabel,
  formatMoney,
  hasTenantPermission,
  initializePilotShell,
  postFormData,
  postJson,
  previewEvidenceContent,
  renderBadge,
  sanitizeFilename,
  stringifyJson,
} from "./shared.js";

function latestItem(items) {
  if (!items || !items.length) {
    return null;
  }
  return [...items].sort((left, right) => {
    const leftTime = Date.parse(
      left.updated_at ||
        left.created_at ||
        left.issued_at ||
        left.receipt_timestamp ||
        left.expires_at ||
        ""
    );
    const rightTime = Date.parse(
      right.updated_at ||
        right.created_at ||
        right.issued_at ||
        right.receipt_timestamp ||
        right.expires_at ||
        ""
    );
    return rightTime - leftTime;
  })[0];
}

function sortTimelineEvents(events) {
  return [...events].sort((left, right) => {
    const leftTime = Date.parse(left.timestamp || "");
    const rightTime = Date.parse(right.timestamp || "");
    if (Number.isNaN(leftTime) && Number.isNaN(rightTime)) {
      return 0;
    }
    if (Number.isNaN(leftTime)) {
      return 1;
    }
    if (Number.isNaN(rightTime)) {
      return -1;
    }
    return leftTime - rightTime;
  });
}

function toneForState(value) {
  switch (value) {
    case "allow":
    case "satisfied":
    case "issued":
    case "reconciled":
    case "matched":
    case "result_observed":
    case "consumed":
    case "succeeded":
      return "allowed";
    case "deny":
    case "structurally_non_executable":
    case "rejected":
    case "failed":
    case "failure_observed":
    case "revoked":
    case "quarantined":
    case "mismatch":
    case "canceled":
      return "blocked";
    case "approval_required":
    case "needs_evidence":
    case "pending":
    case "expired":
    case "requested":
    case "received":
    case "indexed":
    case "manual_review_required":
    case "held":
    case "released":
    case "capability_held":
    case "capability_released":
    case "dispatch_requested":
    case "dispatch_confirmed":
    case "not_provided":
    case "missing":
      return "held";
    default:
      return "neutral";
  }
}

function renderSignalBadge(value, fallback = "not recorded") {
  return renderBadge(value || fallback, toneForState(value));
}

function renderOptionalCode(value, fallback = "Not recorded") {
  return `<span class="pilot-code">${escapeHtml(value || fallback)}</span>`;
}

function isPreviewableMediaType(value) {
  if (!value) {
    return false;
  }
  return (
    value === "application/pdf" ||
    value.startsWith("image/") ||
    value.startsWith("text/") ||
    value === "application/json"
  );
}

function evidenceKindLabel(evidence) {
  if (evidence.storage_mode === "external_uri") {
    return "Reference evidence";
  }
  if (evidence.storage_mode === "inline_metadata_only") {
    return "Metadata-only evidence";
  }
  return "Document evidence";
}

function evidenceActionMarkup(evidence) {
  if (evidence.storage_mode === "external_uri") {
    return `
      <div class="pilot-button-row">
        <button
          class="pilot-button pilot-button--secondary"
          type="button"
          data-evidence-action="open-reference"
          data-evidence-object-id="${escapeHtml(evidence.evidence_object_id)}"
          data-storage-ref="${escapeHtml(evidence.storage_ref)}"
        >
          Open reference
        </button>
      </div>
    `;
  }
  if (evidence.storage_mode === "inline_metadata_only") {
    return `<p class="pilot-inline-note">This evidence stores metadata only. No downloadable file is attached.</p>`;
  }

  const previewButton = isPreviewableMediaType(evidence.media_type || "")
    ? `
      <button
        class="pilot-button pilot-button--secondary"
        type="button"
        data-evidence-action="preview-document"
        data-evidence-object-id="${escapeHtml(evidence.evidence_object_id)}"
      >
        Preview document
      </button>
    `
    : "";
  return `
    <div class="pilot-button-row">
      ${previewButton}
      <button
        class="pilot-button pilot-button--secondary"
        type="button"
        data-evidence-action="download-document"
        data-evidence-object-id="${escapeHtml(evidence.evidence_object_id)}"
        data-original-filename="${escapeHtml(
          evidence.original_filename || `${evidence.evidence_object_id}.bin`
        )}"
      >
        Download document
      </button>
    </div>
  `;
}

function isCurrentPrincipalAssigned(approvalRequest, session) {
  const principal = currentPrincipal(session);
  if (!principal.principalType || !principal.principalId) {
    return false;
  }
  if (!(approvalRequest.assignments || []).length) {
    return !(approvalRequest.eligible_role_ids || []).length;
  }
  return approvalRequest.assignments.some(
    (assignment) =>
      assignment.assignment_status === "assigned" &&
      assignment.principal_type === principal.principalType &&
      assignment.principal_id === principal.principalId
  );
}

function parseOptionalJson(rawValue, fieldName) {
  if (!rawValue.trim()) {
    return {};
  }
  try {
    const parsed = JSON.parse(rawValue);
    if (typeof parsed !== "object" || Array.isArray(parsed) || parsed === null) {
      throw new Error(`${fieldName} must be a JSON object.`);
    }
    return parsed;
  } catch (error) {
    throw new Error(`${fieldName} must be valid JSON.`);
  }
}

function selectedEvidenceIds(form) {
  return [...form.querySelectorAll('input[name="evidence_object_ids"]:checked')].map(
    (input) => input.value
  );
}

function describeApprovalState(action, trace) {
  switch (action.approval_state) {
    case "not_required":
      return "No approval chain was required for this invoice payment.";
    case "pending":
      return `The action is still waiting on ${trace.approvals.length} approval request(s) and ${trace.approval_decisions.length} recorded decision(s).`;
    case "satisfied":
      return "The required approval chain completed successfully.";
    case "rejected":
      return "An approver rejected the action, so it cannot continue.";
    case "expired":
      return "A required approval window expired before the action could continue.";
    case "canceled":
      return "The approval chain was canceled before completion.";
    case "not_started":
    default:
      return "The control plane has not started an approval workflow for this action.";
  }
}

function describeEvidenceState(action, trace) {
  switch (action.evidence_state) {
    case "not_required":
      return "No supporting evidence was required for this invoice payment.";
    case "pending":
      return `The action is still waiting for required evidence. ${trace.evidence_objects.length} evidence object(s) are linked so far.`;
    case "satisfied":
      return `Required evidence has been received. ${trace.evidence_objects.length} evidence object(s) are linked to the action.`;
    case "expired":
      return "A required evidence item expired before the action could continue.";
    case "canceled":
      return "The evidence requirement was canceled before completion.";
    default:
      return "Evidence state has not been recorded yet.";
  }
}

function describeProofState(latestProof) {
  if (!latestProof) {
    return "No proof has been requested or issued for this action yet.";
  }
  switch (latestProof.status) {
    case "requested":
      return "A proof request exists, but the proof has not been issued yet.";
    case "issued":
      return "A bounded proof was issued for this action and is ready to be referenced downstream.";
    case "rejected":
      return "Proof issuance was rejected, so the action cannot move forward on that proof path.";
    case "failed":
      return "Proof issuance failed and needs operator review before the action can proceed.";
    case "revoked":
      return "The previously issued proof has been revoked.";
    case "expired":
      return "The issued proof expired before the action completed.";
    default:
      return "Proof state is present but not fully explained by the current trace.";
  }
}

function describeExecutionState(action, latestEscrow, latestReceipt) {
  if (latestReceipt) {
    if (latestReceipt.outcome === "succeeded") {
      return "A downstream receipt reports successful execution for this action.";
    }
    if (latestReceipt.outcome === "failed") {
      return "A downstream receipt reports a failed execution result.";
    }
    return "A downstream receipt exists, but it does not yet show a final success or failure outcome.";
  }
  if (!latestEscrow) {
    return "The action has not yet entered the capability release path.";
  }
  switch (latestEscrow.status) {
    case "held":
      return "Capability is still held by the control plane and has not been released.";
    case "released":
      return "Capability was released, but a downstream result has not yet been observed.";
    case "consumed":
      return "Capability was consumed and the action is waiting for a downstream result or receipt.";
    case "revoked":
      return "Capability release was revoked before completion.";
    case "quarantined":
      return "Capability release is quarantined pending review.";
    case "expired":
      return "Capability release expired before a final outcome was recorded.";
    default:
      return `Execution state is currently ${formatLabel(action.execution_state)}.`;
  }
}

function describeReceiptState(action, trace, latestReceipt, latestReconciliation) {
  if (!latestReceipt) {
    return "No receipt has been ingested for this action yet.";
  }
  if (latestReconciliation?.status === "matched") {
    return "A receipt has been ingested and the recorded links match the action, proof, and release data that were available.";
  }
  if (latestReconciliation?.status === "manual_review_required") {
    return "A receipt exists, but at least one reconciliation check needs human review.";
  }
  if (latestReconciliation?.status === "mismatch") {
    return "A receipt exists, but at least one reconciliation check did not match the linked action state.";
  }
  return `Receipt state is ${formatLabel(action.receipt_state)} with ${trace.receipts.length} receipt record(s) linked.`;
}

function describeFinalRecordedState(action, latestReceipt, latestEscrow) {
  if (latestReceipt) {
    if (latestReceipt.outcome === "succeeded") {
      return {
        label: "execution succeeded",
        tone: "allowed",
        detail: "The latest receipt shows a successful outcome for this invoice payment.",
      };
    }
    if (latestReceipt.outcome === "failed") {
      return {
        label: "execution failed",
        tone: "blocked",
        detail: "The latest receipt shows a failed outcome for this invoice payment.",
      };
    }
    return {
      label: formatLabel(action.execution_state),
      tone: toneForState(action.execution_state),
      detail: "A receipt is present, but the final downstream outcome is not marked as succeeded or failed.",
    };
  }
  if (latestEscrow?.status === "released" || latestEscrow?.status === "consumed") {
    return {
      label: "waiting for receipt",
      tone: "held",
      detail: "Capability moved forward, but the control plane has not ingested a final receipt yet.",
    };
  }
  if (action.decision_state === "deny" || action.decision_state === "structurally_non_executable") {
    return {
      label: "stopped before execution",
      tone: "blocked",
      detail: "The action was blocked before any release or execution step could continue.",
    };
  }
  return {
    label: formatLabel(action.execution_state),
    tone: toneForState(action.execution_state),
    detail: "The control flow is still in progress and no final downstream result has been recorded yet.",
  };
}

function renderStatusCard({ eyebrow, title, detail, badges, tone = "neutral" }) {
  return `
    <article class="pilot-status-card" data-tone="${escapeHtml(tone)}">
      <div class="pilot-status-card__eyebrow">${escapeHtml(eyebrow)}</div>
      ${badges ? `<div class="pilot-badges">${badges}</div>` : ""}
      <h4>${escapeHtml(title)}</h4>
      <p>${escapeHtml(detail)}</p>
    </article>
  `;
}

function renderHeader(action, trace, latestProof, latestEscrow, latestReceipt) {
  const outcome = deriveOutcome(action, latestProof?.status || null);
  const lifecycle = deriveLifecycleStage(action, latestProof?.status || null);
  const operatorStatus = deriveOperatorStatus(action, latestProof?.status || null);
  const receiptAvailability = deriveReceiptAvailability(action);
  const visibleOutcomeLabel = outcome.label === "blocked" ? "blocked / refused" : outcome.label;
  const proofBadge = latestProof
    ? renderSignalBadge(latestProof.status)
    : renderBadge("proof not requested", "neutral");
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <div class="pilot-badges">
            <a href="/pilot/actions">Back to invoice payment actions</a>
            <a href="/pilot/review">Open held and exceptions queue</a>
          </div>
          <h2>${escapeHtml(deriveInvoiceReference(action))}</h2>
          <p>
            Stored action type: ${escapeHtml(action.finance_action_class || action.action_intent_payload.action_type || "not provided")}
            · Workflow: ${escapeHtml(action.workflow_key)}
          </p>
          <p class="pilot-inline-note">Last updated ${escapeHtml(formatDateTime(action.updated_at))}</p>
        </div>
        <button id="trace-export" class="pilot-button pilot-button--secondary" type="button">Export trace JSON</button>
      </div>
      <div class="pilot-status-grid">
        ${renderStatusCard({
          eyebrow: "Control outcome",
          title: visibleOutcomeLabel,
          detail: outcome.reason,
          badges: renderBadge(visibleOutcomeLabel, outcome.tone),
          tone: outcome.tone,
        })}
        ${renderStatusCard({
          eyebrow: "Lifecycle state",
          title: lifecycle.label,
          detail: lifecycle.detail,
          badges: renderBadge(lifecycle.label, lifecycle.tone),
          tone: lifecycle.tone,
        })}
        ${renderStatusCard({
          eyebrow: "Reviewability",
          title: operatorStatus.label,
          detail: `${operatorStatus.detail} Next step: ${operatorStatus.nextStep}.`,
          badges: renderBadge(operatorStatus.label, operatorStatus.tone),
          tone: operatorStatus.tone,
        })}
        ${renderStatusCard({
          eyebrow: "Approval state",
          title: formatLabel(action.approval_state),
          detail: describeApprovalState(action, trace),
          badges: `
            ${renderSignalBadge(action.approval_state)}
            ${renderBadge(`${trace.approvals.length} request(s)`, "neutral")}
            ${renderBadge(`${trace.approval_decisions.length} decision(s)`, "neutral")}
          `,
          tone: toneForState(action.approval_state),
        })}
        ${renderStatusCard({
          eyebrow: "Evidence state",
          title: formatLabel(action.evidence_state),
          detail: describeEvidenceState(action, trace),
          badges: `
            ${renderSignalBadge(action.evidence_state)}
            ${renderBadge(`${trace.evidence_objects.length} linked`, "neutral")}
          `,
          tone: toneForState(action.evidence_state),
        })}
        ${renderStatusCard({
          eyebrow: "Receipt and export availability",
          title: receiptAvailability.label,
          detail: `${receiptAvailability.detail} Trace export ready from this page.`,
          badges: `
            ${proofBadge}
            ${renderBadge(receiptAvailability.label, receiptAvailability.tone)}
            ${renderBadge("trace export ready", "neutral")}
          `,
          tone: receiptAvailability.tone,
        })}
      </div>
      <hr class="pilot-divider">
      <div class="pilot-grid pilot-grid--three">
        <div class="pilot-metadata">
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">External reference</span>
            <span class="pilot-metadata__value">${escapeHtml(action.external_reference || "Not provided")}</span>
          </div>
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Payee or supplier</span>
            <span class="pilot-metadata__value">${escapeHtml(derivePayeeReference(action))}</span>
          </div>
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Requested by</span>
            <span class="pilot-metadata__value">${escapeHtml(action.requested_by_principal_type)} · ${escapeHtml(action.requested_by_principal_id)}</span>
          </div>
        </div>
        <div class="pilot-metadata">
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Amount</span>
            <span class="pilot-metadata__value">${escapeHtml(formatMoney(action.finance_index.amount_minor, action.finance_index.currency))}</span>
          </div>
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Source account</span>
            <span class="pilot-metadata__value">${escapeHtml(action.finance_index.source_account_ref || "Not provided")}</span>
          </div>
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Destination account</span>
            <span class="pilot-metadata__value">${escapeHtml(action.finance_index.destination_account_ref || "Not provided")}</span>
          </div>
        </div>
        <div class="pilot-metadata">
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Action record</span>
            <span class="pilot-metadata__value pilot-code">${escapeHtml(action.action_intent_record_id)}</span>
          </div>
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Action digest</span>
            <span class="pilot-metadata__value pilot-code">${escapeHtml(action.action_intent_digest)}</span>
          </div>
          <div class="pilot-metadata__row">
            <span class="pilot-metadata__label">Execution result</span>
            <span class="pilot-metadata__value">${escapeHtml(latestReceipt?.outcome || trace.summary.execution_state)}</span>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderDecisionRationale(
  action,
  trace,
  latestProof,
  latestEscrow,
  latestReceipt,
  evidenceDetails
) {
  const outcome = deriveOutcome(action, latestProof?.status || null);
  const finalState = describeFinalRecordedState(action, latestReceipt, latestEscrow);
  const latestReconciliation = latestItem(trace.reconciliation_records);
  const checkpoints = [
    {
      title: "Policy intake",
      state: action.decision_state,
      detail: action.decision_reason,
      meta: `Contract validation: ${formatLabel(action.contract_validation_status)}`,
    },
    {
      title: "Approval checks",
      state: action.approval_state,
      detail: describeApprovalState(action, trace),
      meta: `${trace.approvals.length} request(s) · ${trace.approval_decisions.length} decision(s)`,
    },
    {
      title: "Evidence received",
      state: action.evidence_state,
      detail: describeEvidenceState(action, trace),
      meta: `${trace.evidence_objects.length} evidence object(s) linked`,
    },
    {
      title: "Proof stage",
      state: latestProof?.status || "not_requested",
      detail: describeProofState(latestProof),
      meta: latestProof
        ? `Audience ${latestProof.audience}`
        : "Proof has not been requested yet.",
    },
    {
      title: "Execution state",
      state: latestEscrow?.execution_state || action.execution_state,
      detail: describeExecutionState(action, latestEscrow, latestReceipt),
      meta: latestEscrow
        ? `Escrow status: ${formatLabel(latestEscrow.status)}`
        : "No escrow release record yet.",
    },
    {
      title: "Receipt trail",
      state: action.receipt_state,
      detail: describeReceiptState(action, trace, latestReceipt, latestReconciliation),
      meta: latestReceipt
        ? `Latest receipt: ${latestReceipt.external_receipt_id}`
        : "No receipt record yet.",
    },
  ];

  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Decision rationale</h3>
          <p>This section explains why the control plane currently treats this invoice payment as allowed, held, or blocked.</p>
        </div>
      </div>
      <div class="pilot-grid pilot-grid--two">
        <article class="pilot-callout pilot-callout--${outcome.tone}">
          <div class="pilot-callout__eyebrow">Current control outcome</div>
          <h4>${escapeHtml(formatLabel(outcome.label))}</h4>
          <p>${escapeHtml(outcome.reason)}</p>
        </article>
        <article class="pilot-callout pilot-callout--${finalState.tone}">
          <div class="pilot-callout__eyebrow">Final recorded state</div>
          <h4>${escapeHtml(finalState.label)}</h4>
          <p>${escapeHtml(finalState.detail)}</p>
        </article>
      </div>
      <div class="pilot-grid pilot-grid--three">
        ${checkpoints
          .map(
            (checkpoint) => `
              <article class="pilot-checkpoint">
                <div class="pilot-checkpoint__header">
                  <h4>${escapeHtml(checkpoint.title)}</h4>
                  ${renderSignalBadge(checkpoint.state)}
                </div>
                <p>${escapeHtml(checkpoint.detail)}</p>
                <p class="pilot-inline-note">${escapeHtml(checkpoint.meta)}</p>
              </article>
            `
          )
          .join("")}
      </div>
      <div class="pilot-grid pilot-grid--two">
        <article class="pilot-list__item">
          <h4>Control inputs</h4>
          <p>Matched rule: ${escapeHtml(action.matched_rule_id || "No tenant rule recorded")}</p>
          <p>Workflow profile: ${escapeHtml(action.workflow_binding?.workflow_profile || "Not provided")}</p>
          <p>Risk tier: ${escapeHtml(action.finance_routing_context?.risk_tier || "Not provided")}</p>
        </article>
        <article class="pilot-list__item">
          <h4>Requirement snapshots</h4>
          <p>Approval requirement</p>
          <pre class="pilot-pre">${escapeHtml(stringifyJson(action.approval_requirement))}</pre>
          <p>Evidence requirement</p>
          <pre class="pilot-pre">${escapeHtml(stringifyJson(action.evidence_requirement))}</pre>
        </article>
      </div>
      <div class="pilot-grid pilot-grid--two">
        <article class="pilot-list__item">
          <h4>Evidence received</h4>
          ${
            evidenceDetails.length
              ? `
                <div class="pilot-list">
                  ${evidenceDetails
                    .map(
                      (evidence) => `
                        <article class="pilot-subcard">
                          <div class="pilot-subcard__header">
                            <span>${escapeHtml(formatLabel(evidence.evidence_type))}</span>
                            <div class="pilot-badges">
                              ${renderBadge(evidenceKindLabel(evidence), "neutral")}
                              ${renderSignalBadge(evidence.status)}
                            </div>
                          </div>
                          <p>Storage mode: ${escapeHtml(formatLabel(evidence.storage_mode))}</p>
                          <p>Filename: ${escapeHtml(evidence.original_filename || "Not recorded")}</p>
                          <p>Media type: ${escapeHtml(evidence.media_type || "Not recorded")}</p>
                          <p>Created: ${escapeHtml(formatDateTime(evidence.created_at))}</p>
                          <p>Approval request: ${escapeHtml(evidence.approval_request_id || "General action evidence")}</p>
                          ${evidenceActionMarkup(evidence)}
                          <details>
                            <summary>Evidence metadata</summary>
                            <pre class="pilot-pre">${escapeHtml(stringifyJson(evidence.evidence_metadata))}</pre>
                          </details>
                        </article>
                      `
                    )
                    .join("")}
                </div>
              `
              : `<p class="pilot-empty">No evidence objects are currently linked to this action.</p>`
          }
        </article>
        <article class="pilot-list__item">
          <h4>What the operator can trust here</h4>
          <p>The outcome text above is derived from stored decision, approval, evidence, proof, execution, and receipt state.</p>
          <p>The UI does not invent policy reasoning beyond the recorded decision reason and evaluation trace.</p>
          <p>The final result stays provisional until a receipt is ingested and reconciled.</p>
        </article>
      </div>
      <details class="pilot-card" open>
        <summary><strong>Evaluation trace</strong></summary>
        <pre class="pilot-pre">${escapeHtml(stringifyJson(action.evaluation_trace))}</pre>
      </details>
      <details class="pilot-card">
        <summary><strong>Stored action payload</strong></summary>
        <pre class="pilot-pre">${escapeHtml(stringifyJson(action.action_intent_payload))}</pre>
      </details>
    </section>
  `;
}

function renderPermissionSummary(session, tenantId) {
  return `
    <div class="pilot-badges">
      ${renderBadge(
        hasTenantPermission(session, tenantId, "tenant.approval.write")
          ? "approval actions enabled"
          : "approval read only",
        hasTenantPermission(session, tenantId, "tenant.approval.write") ? "allowed" : "neutral"
      )}
      ${renderBadge(
        hasTenantPermission(session, tenantId, "tenant.evidence.write")
          ? "evidence actions enabled"
          : "evidence read only",
        hasTenantPermission(session, tenantId, "tenant.evidence.write") ? "allowed" : "neutral"
      )}
    </div>
  `;
}

function renderApprovalDecisionForms(approvalRequests, trace, session, allowRequestEvidence) {
  const reviewableRequests = approvalRequests.filter((request) => request.status === "pending");
  const evidenceChoices = trace.evidence_objects.filter((evidence) => evidence.status === "active");

  if (!reviewableRequests.length) {
    return `<p class="pilot-empty">No open approval request currently needs a decision.</p>`;
  }

  return reviewableRequests
    .map((approvalRequest) => {
      const assigned = isCurrentPrincipalAssigned(approvalRequest, session);
      if (!assigned) {
        const assignmentText = approvalRequest.assignments.length
          ? "The current token is not assigned to this approval request."
          : "This approval request has no explicit assignment, but role-based approval matching is not exposed in the current pilot session payload.";
        return `
          <article class="pilot-subcard">
            <div class="pilot-subcard__header">
              <span>${escapeHtml(approvalRequest.approval_group_key)}</span>
              ${renderSignalBadge(approvalRequest.status)}
            </div>
            <p>${escapeHtml(assignmentText)}</p>
            <p>Required decisions: ${escapeHtml(String(approvalRequest.required_decision_count))}</p>
          </article>
        `;
      }

      return `
        <form class="pilot-form pilot-form--stack" data-approval-form data-approval-request-id="${escapeHtml(approvalRequest.approval_request_id)}">
          <article class="pilot-subcard">
            <div class="pilot-subcard__header">
              <span>${escapeHtml(approvalRequest.approval_group_key)}</span>
              ${renderSignalBadge(approvalRequest.status)}
            </div>
            <p>Required decisions: ${escapeHtml(String(approvalRequest.required_decision_count))}</p>
            <p>Expires: ${escapeHtml(formatDateTime(approvalRequest.expires_at))}</p>
            <div class="pilot-field">
              <label>Decision reason</label>
              <textarea name="decision_reason" rows="3" placeholder="Explain why this invoice payment should be approved or declined"></textarea>
            </div>
            ${
              evidenceChoices.length
                ? `
                  <fieldset class="pilot-fieldset">
                    <legend>Link active evidence to this decision</legend>
                    <div class="pilot-stack">
                      ${evidenceChoices
                        .map(
                          (evidence) => `
                            <label class="pilot-checkbox">
                              <input type="checkbox" name="evidence_object_ids" value="${escapeHtml(evidence.evidence_object_id)}">
                              <span>${escapeHtml(formatLabel(evidence.evidence_type))} · ${escapeHtml(evidence.evidence_object_id)}</span>
                            </label>
                          `
                        )
                        .join("")}
                    </div>
                  </fieldset>
                `
                : `<p class="pilot-inline-note">No active evidence objects are currently available to cite with this decision.</p>`
            }
            <div class="pilot-button-row">
              <button class="pilot-button pilot-button--primary" type="button" data-decision="approve">Approve</button>
              <button class="pilot-button pilot-button--secondary" type="button" data-decision="reject">Decline</button>
              ${
                allowRequestEvidence
                  ? `<button class="pilot-button pilot-button--secondary" type="button" data-request-evidence>Request evidence</button>`
                  : ""
              }
            </div>
          </article>
        </form>
      `;
    })
    .join("");
}

function renderEvidenceControls(action, approvalRequests, session) {
  const approvalOptions = [
    `<option value="">General action evidence</option>`,
    ...approvalRequests
      .filter((request) => request.status === "pending")
      .map(
        (request) =>
          `<option value="${escapeHtml(request.approval_request_id)}">${escapeHtml(
            request.approval_group_key
          )} · ${escapeHtml(request.approval_request_id)}</option>`
      ),
  ].join("");

  if (!hasTenantPermission(session, action.tenant_id, "tenant.evidence.write")) {
    return `<p class="pilot-empty">The current token can view evidence state, but it cannot upload or register evidence.</p>`;
  }

  return `
    <div class="pilot-grid pilot-grid--two">
      <form class="pilot-form pilot-form--stack" id="evidence-upload-form">
        <article class="pilot-subcard">
          <div class="pilot-subcard__header">
            <span>Upload evidence</span>
            ${renderBadge("filesystem", "neutral")}
          </div>
          <div class="pilot-field">
            <label for="upload-approval-request">Bind to approval request</label>
            <select id="upload-approval-request" name="approval_request_id">${approvalOptions}</select>
          </div>
          <div class="pilot-field">
            <label for="upload-evidence-type">Evidence type</label>
            <select id="upload-evidence-type" name="evidence_type">
              <option value="document">document</option>
              <option value="attestation">attestation</option>
              <option value="external_reference">external_reference</option>
              <option value="export">export</option>
              <option value="policy_attachment">policy_attachment</option>
            </select>
          </div>
          <div class="pilot-field">
            <label for="upload-file">File</label>
            <input id="upload-file" name="file" type="file" required>
          </div>
          <div class="pilot-field">
            <label for="upload-expires-at">Expires at (optional ISO-8601)</label>
            <input id="upload-expires-at" name="expires_at" type="text" placeholder="2026-05-01T12:00:00+00:00">
          </div>
          <div class="pilot-field">
            <label for="upload-evidence-metadata">Evidence metadata JSON</label>
            <textarea id="upload-evidence-metadata" name="evidence_metadata_json" rows="4" placeholder='{"source":"operator-upload"}'></textarea>
          </div>
          <div class="pilot-button-row">
            <button class="pilot-button pilot-button--primary" type="submit">Upload evidence</button>
          </div>
        </article>
      </form>
      <form class="pilot-form pilot-form--stack" id="evidence-register-form">
        <article class="pilot-subcard">
          <div class="pilot-subcard__header">
            <span>Register external evidence</span>
            ${renderBadge("external reference", "neutral")}
          </div>
          <div class="pilot-field">
            <label for="register-approval-request">Bind to approval request</label>
            <select id="register-approval-request" name="approval_request_id">${approvalOptions}</select>
          </div>
          <div class="pilot-field">
            <label for="register-storage-mode">Storage mode</label>
            <select id="register-storage-mode" name="storage_mode">
              <option value="external_uri">external_uri</option>
              <option value="inline_metadata_only">inline_metadata_only</option>
            </select>
          </div>
          <div class="pilot-field">
            <label for="register-evidence-type">Evidence type</label>
            <select id="register-evidence-type" name="evidence_type">
              <option value="document">document</option>
              <option value="attestation">attestation</option>
              <option value="external_reference">external_reference</option>
              <option value="export">export</option>
              <option value="policy_attachment">policy_attachment</option>
            </select>
          </div>
          <div class="pilot-field">
            <label for="register-storage-ref">Storage reference</label>
            <input id="register-storage-ref" name="storage_ref" type="text" placeholder="https://..." required>
          </div>
          <div class="pilot-field">
            <label for="register-original-filename">Original filename (optional)</label>
            <input id="register-original-filename" name="original_filename" type="text" placeholder="wire-proof.pdf">
          </div>
          <div class="pilot-field">
            <label for="register-media-type">Media type (optional)</label>
            <input id="register-media-type" name="media_type" type="text" placeholder="application/pdf">
          </div>
          <div class="pilot-field">
            <label for="register-expires-at">Expires at (optional ISO-8601)</label>
            <input id="register-expires-at" name="expires_at" type="text" placeholder="2026-05-01T12:00:00+00:00">
          </div>
          <div class="pilot-field">
            <label for="register-evidence-metadata">Evidence metadata JSON</label>
            <textarea id="register-evidence-metadata" name="evidence_metadata_json" rows="4" placeholder='{"source":"case-management"}'></textarea>
          </div>
          <div class="pilot-button-row">
            <button class="pilot-button pilot-button--primary" type="submit">Register evidence</button>
          </div>
        </article>
      </form>
    </div>
  `;
}

function renderOperatorWorkflow(action, trace, approvalRequests, session, latestProof) {
  const disposition = deriveReviewDisposition(action, latestProof?.status || null);
  const reviewableApproval = action.approval_state === "pending";
  const reviewableEvidence =
    action.evidence_state === "pending" || action.evidence_state === "expired";

  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Operator review</h3>
          <p>This section only exposes operator actions the backend already supports for the invoice payment pilot.</p>
        </div>
      </div>
      <article class="pilot-callout pilot-callout--${disposition.tone}">
        <div class="pilot-callout__eyebrow">Operator queue status</div>
        <h4>${escapeHtml(disposition.label)}</h4>
        <p>${escapeHtml(disposition.reason)}</p>
        <p class="pilot-inline-note">Next step: ${escapeHtml(disposition.nextStep)}</p>
      </article>
      ${renderPermissionSummary(session, action.tenant_id)}
      ${
        disposition.bucket === "blocked"
          ? `
            <p class="pilot-empty">
              This outcome is blocked by policy or structure. The current pilot UI does not expose an override path for blocked actions.
            </p>
          `
          : ""
      }
      ${
        reviewableApproval
          ? `
            <section class="pilot-stack">
              <div class="pilot-section-header">
                <div>
                  <h4>Approval decisions</h4>
                  <p>Approve or decline only if the current token is assigned to the open approval request.${reviewableEvidence ? " Use request evidence to jump to the evidence action forms when supporting material is still needed." : ""}</p>
                </div>
              </div>
              ${hasTenantPermission(session, action.tenant_id, "tenant.approval.write")
                ? renderApprovalDecisionForms(
                    approvalRequests,
                    trace,
                    session,
                    reviewableEvidence
                  )
                : `<p class="pilot-empty">The current token cannot submit approval decisions.</p>`}
            </section>
          `
          : ""
      }
      ${
        reviewableEvidence
          ? `
            <section id="evidence-actions" class="pilot-stack">
              <div class="pilot-section-header">
                <div>
                  <h4>Evidence actions</h4>
                  <p>Upload a file or register an external reference so the held action can satisfy its evidence requirement.</p>
                </div>
              </div>
              ${renderEvidenceControls(action, approvalRequests, session)}
            </section>
          `
          : ""
      }
      ${
        disposition.bucket === "follow_up"
          ? `
            <section class="pilot-card pilot-card--warning">
              <h4>Manual follow-up</h4>
              <p>
                The current pilot backend does not yet persist operator notes, escalation state, or follow-up ownership for this condition.
                Use the trace export and current runbook outside the product for follow-up.
              </p>
            </section>
          `
          : ""
      }
      ${
        !reviewableApproval && !reviewableEvidence && disposition.bucket === "reviewable"
          ? `<p class="pilot-empty">This action is held, but there is no direct review transition exposed in the current UI yet.</p>`
          : ""
      }
    </section>
  `;
}

function renderTimelineStage(stageNumber, title, stateBadges, description, metaLines) {
  return `
    <article class="pilot-timeline__item">
      <div class="pilot-timeline__row">
        <div>
          <div class="pilot-timeline__eyebrow">Step ${stageNumber}</div>
          <h4>${escapeHtml(title)}</h4>
        </div>
        <div class="pilot-badges">${stateBadges}</div>
      </div>
      <div class="pilot-timeline__body">
        <p>${escapeHtml(description)}</p>
        ${
          metaLines.length
            ? `
              <div class="pilot-timeline__meta">
                ${metaLines.map((line) => `<span>${escapeHtml(line)}</span>`).join("")}
              </div>
            `
            : ""
        }
      </div>
    </article>
  `;
}

function renderTimeline(action, trace, latestProof, latestEscrow, latestReceipt) {
  const latestReconciliation = latestItem(trace.reconciliation_records);
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Lifecycle timeline</h3>
          <p>The stages below separate intake, checks, proof, execution, and receipt trail so operators can see exactly where the action moved or stopped.</p>
        </div>
      </div>
      <div class="pilot-timeline">
        ${renderTimelineStage(
          1,
          "Action entered control plane",
          renderSignalBadge(action.decision_state),
          action.decision_reason,
          [
            `Created ${formatDateTime(action.created_at)}`,
            `Workflow ${action.workflow_key}`,
            `Contract ${formatLabel(action.contract_validation_status)}`,
          ]
        )}
        ${renderTimelineStage(
          2,
          "Approval checks",
          renderSignalBadge(action.approval_state),
          describeApprovalState(action, trace),
          [
            `${trace.approvals.length} approval request(s)`,
            `${trace.approval_decisions.length} approval decision(s)`,
          ]
        )}
        ${renderTimelineStage(
          3,
          "Evidence received",
          renderSignalBadge(action.evidence_state),
          describeEvidenceState(action, trace),
          [`${trace.evidence_objects.length} evidence object(s) linked`]
        )}
        ${renderTimelineStage(
          4,
          "Proof progression",
          latestProof ? renderSignalBadge(latestProof.status) : renderBadge("not requested", "neutral"),
          describeProofState(latestProof),
          latestProof
            ? [
                `Audience ${latestProof.audience}`,
                `Issued ${formatDateTime(latestProof.issued_at)}`,
                `Expires ${formatDateTime(latestProof.expires_at)}`,
              ]
            : ["No proof record linked yet"]
        )}
        ${renderTimelineStage(
          5,
          "Release and execution",
          `
            ${latestEscrow ? renderSignalBadge(latestEscrow.status) : renderBadge("no escrow", "neutral")}
            ${renderSignalBadge(action.execution_state)}
          `,
          describeExecutionState(action, latestEscrow, latestReceipt),
          latestEscrow
            ? [
                `Protected resource ${latestEscrow.protected_resource_ref}`,
                `Provider execution ${latestEscrow.provider_execution_ref || "not observed"}`,
              ]
            : ["Capability release has not been created yet"]
        )}
        ${renderTimelineStage(
          6,
          "Receipt and final state",
          `
            ${renderSignalBadge(action.receipt_state)}
            ${latestReconciliation ? renderSignalBadge(latestReconciliation.status) : renderBadge("not reconciled", "neutral")}
          `,
          describeReceiptState(action, trace, latestReceipt, latestReconciliation),
          latestReceipt
            ? [
                `Outcome ${latestReceipt.outcome}`,
                `Occurred ${formatDateTime(latestReceipt.receipt_timestamp)}`,
                `Receipt ${latestReceipt.external_receipt_id}`,
              ]
            : ["No receipt has been ingested yet"]
        )}
      </div>
    </section>
  `;
}

function renderApprovalProgress(trace, action) {
  const events = sortTimelineEvents([
    ...trace.approvals.map((approval) => ({
      kind: "approval request created",
      title: approval.approval_group_key,
      state: approval.status,
      detail: `${approval.required_decision_count} decision(s) required`,
      meta: approval.expires_at
        ? `Expires ${formatDateTime(approval.expires_at)}`
        : "No expiry recorded",
      timestamp: approval.created_at,
    })),
    ...trace.approval_decisions.map((decision) => ({
      kind: "approval decision recorded",
      title: `${decision.decided_by_principal_type} · ${decision.decided_by_principal_id}`,
      state: decision.decision,
      detail: decision.decision_reason || "No decision reason recorded",
      meta: decision.evidence_object_ids.length
        ? `Linked evidence: ${decision.evidence_object_ids.join(", ")}`
        : "No evidence IDs linked to this decision",
      timestamp: decision.created_at,
    })),
  ]);

  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Approval progression</h3>
          <p>The approval chain is shown as a timeline so operators can see what was requested, who responded, and whether the chain is complete.</p>
        </div>
      </div>
      <article class="pilot-callout pilot-callout--${toneForState(action.approval_state)}">
        <div class="pilot-callout__eyebrow">Current approval state</div>
        <h4>${escapeHtml(formatLabel(action.approval_state))}</h4>
        <p>${escapeHtml(describeApprovalState(action, trace))}</p>
      </article>
      ${
        events.length
          ? `
            <div class="pilot-event-list">
              ${events
                .map(
                  (event) => `
                    <article class="pilot-event">
                      <div class="pilot-event__header">
                        <div>
                          <div class="pilot-timeline__eyebrow">${escapeHtml(event.kind)}</div>
                          <h4>${escapeHtml(event.title)}</h4>
                        </div>
                        ${renderSignalBadge(event.state)}
                      </div>
                      <p>${escapeHtml(event.detail)}</p>
                      <div class="pilot-timeline__meta">
                        <span>${escapeHtml(event.meta)}</span>
                        <span>${escapeHtml(formatDateTime(event.timestamp))}</span>
                      </div>
                    </article>
                  `
                )
                .join("")}
            </div>
          `
          : `<p class="pilot-empty">No approval requests or approval decisions are currently linked to this action.</p>`
      }
    </section>
  `;
}

function renderProofPanel(trace) {
  const latestProof = latestItem(trace.issued_proofs);
  return `
    <article class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Proof progression</h3>
          <p>This panel shows proof issuance state only. Verification is handled through the separate verifier dependency when required downstream.</p>
        </div>
      </div>
      <article class="pilot-callout pilot-callout--${toneForState(latestProof?.status || "not_requested")}">
        <div class="pilot-callout__eyebrow">Current proof state</div>
        <h4>${escapeHtml(formatLabel(latestProof?.status || "not_requested"))}</h4>
        <p>${escapeHtml(describeProofState(latestProof))}</p>
      </article>
      ${
        trace.issued_proofs.length
          ? `
            <div class="pilot-event-list">
              ${trace.issued_proofs
                .map(
                  (proof) => `
                    <article class="pilot-event">
                      <div class="pilot-event__header">
                        <div>
                          <div class="pilot-timeline__eyebrow">Proof record</div>
                          <h4>${escapeHtml(proof.issued_proof_id)}</h4>
                        </div>
                        ${renderSignalBadge(proof.status)}
                      </div>
                      <p>${escapeHtml(formatLabel(proof.proof_kind))} bound to audience ${proof.audience}.</p>
                      <div class="pilot-timeline__meta">
                        <span>Scope ${escapeHtml(proof.scope.join(", "))}</span>
                        <span>Issued ${escapeHtml(formatDateTime(proof.issued_at))}</span>
                        <span>Expires ${escapeHtml(formatDateTime(proof.expires_at))}</span>
                      </div>
                      <details>
                        <summary>Binding details</summary>
                        <div class="pilot-metadata">
                          <div class="pilot-metadata__row">
                            <span class="pilot-metadata__label">Nonce</span>
                            <span class="pilot-metadata__value pilot-code">${escapeHtml(proof.nonce)}</span>
                          </div>
                          <div class="pilot-metadata__row">
                            <span class="pilot-metadata__label">Action digest</span>
                            <span class="pilot-metadata__value pilot-code">${escapeHtml(proof.action_intent_digest)}</span>
                          </div>
                        </div>
                      </details>
                    </article>
                  `
                )
                .join("")}
            </div>
          `
          : `<p class="pilot-empty">No proof has been issued for this action yet.</p>`
      }
    </article>
  `;
}

function renderExecutionPanel(trace, action) {
  const latestEscrow = latestItem(trace.escrow_records);
  const latestReceipt = latestItem(trace.receipts);
  const finalState = describeFinalRecordedState(action, latestReceipt, latestEscrow);

  return `
    <article class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Execution progression</h3>
          <p>This panel shows release and execution records already stored in the control plane. Final external outcome is only confirmed once a receipt is ingested.</p>
        </div>
      </div>
      <article class="pilot-callout pilot-callout--${toneForState(action.execution_state)}">
        <div class="pilot-callout__eyebrow">Current execution state</div>
        <h4>${escapeHtml(formatLabel(action.execution_state))}</h4>
        <p>${escapeHtml(describeExecutionState(action, latestEscrow, latestReceipt))}</p>
      </article>
      <article class="pilot-callout pilot-callout--${finalState.tone}">
        <div class="pilot-callout__eyebrow">Best recorded outcome</div>
        <h4>${escapeHtml(finalState.label)}</h4>
        <p>${escapeHtml(finalState.detail)}</p>
      </article>
      ${
        trace.escrow_records.length
          ? `
            <div class="pilot-event-list">
              ${trace.escrow_records
                .map(
                  (escrow) => `
                    <article class="pilot-event">
                      <div class="pilot-event__header">
                        <div>
                          <div class="pilot-timeline__eyebrow">Execution record</div>
                          <h4>${escapeHtml(escrow.escrow_record_id)}</h4>
                        </div>
                        <div class="pilot-badges">
                          ${renderSignalBadge(escrow.status)}
                          ${renderSignalBadge(escrow.execution_state)}
                        </div>
                      </div>
                      <p>${escapeHtml(escrow.capability_kind)} capability for ${escapeHtml(escrow.protected_resource_ref)}.</p>
                      <div class="pilot-timeline__meta">
                        <span>Created ${escapeHtml(formatDateTime(escrow.created_at))}</span>
                        <span>Provider execution ${escapeHtml(escrow.provider_execution_ref || "not observed")}</span>
                      </div>
                    </article>
                  `
                )
                .join("")}
            </div>
          `
          : `<p class="pilot-empty">No release or execution records are currently linked to this action.</p>`
      }
    </article>
  `;
}

function renderReconciliationChecks(records) {
  if (!records.length) {
    return "";
  }
  return `
    <details>
      <summary>Reconciliation checks</summary>
      <div class="pilot-check-list">
        ${records
          .map(
            (record) => `
              <article class="pilot-check-item">
                <div class="pilot-subcard__header">
                  <span>${escapeHtml(formatLabel(record.reconciliation_type))}</span>
                  ${renderSignalBadge(record.status)}
                </div>
                <p>${escapeHtml(record.summary)}</p>
                <div class="pilot-list">
                  ${record.checks
                    .map(
                      (check) => `
                        <article class="pilot-subcard">
                          <div class="pilot-subcard__header">
                            <span>${escapeHtml(check.field)}</span>
                            ${renderSignalBadge(check.status)}
                          </div>
                          <p>Expected: ${escapeHtml(JSON.stringify(check.expected))}</p>
                          <p>Actual: ${escapeHtml(JSON.stringify(check.actual))}</p>
                        </article>
                      `
                    )
                    .join("")}
                </div>
              </article>
            `
          )
          .join("")}
      </div>
    </details>
  `;
}

function renderReceiptPanel(trace, action) {
  const latestReceipt = latestItem(trace.receipts);
  const reconciliationByReceiptId = new Map();
  for (const record of trace.reconciliation_records) {
    const group = reconciliationByReceiptId.get(record.receipt_id) || [];
    group.push(record);
    reconciliationByReceiptId.set(record.receipt_id, group);
  }
  const latestReconciliation = latestItem(trace.reconciliation_records);

  return `
    <article class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Receipt progression</h3>
          <p>This panel shows what was received back from execution and how that receipt lines up with the action, proof, and release records.</p>
        </div>
      </div>
      <article class="pilot-callout pilot-callout--${toneForState(latestReconciliation?.status || action.receipt_state)}">
        <div class="pilot-callout__eyebrow">Current receipt state</div>
        <h4>${escapeHtml(formatLabel(action.receipt_state))}</h4>
        <p>${escapeHtml(describeReceiptState(action, trace, latestReceipt, latestReconciliation))}</p>
      </article>
      ${
        trace.receipts.length
          ? `
            <div class="pilot-event-list">
              ${trace.receipts
                .map((receipt) => {
                  const reconciliationRecords =
                    reconciliationByReceiptId.get(receipt.receipt_id) || [];
                  return `
                    <article class="pilot-event">
                      <div class="pilot-event__header">
                        <div>
                          <div class="pilot-timeline__eyebrow">Receipt ingested</div>
                          <h4>${escapeHtml(receipt.external_receipt_id)}</h4>
                        </div>
                        <div class="pilot-badges">
                          ${renderSignalBadge(receipt.receipt_state)}
                          ${renderSignalBadge(receipt.outcome)}
                        </div>
                      </div>
                      <p>${escapeHtml(formatLabel(receipt.receipt_type))} receipt recorded for this invoice payment.</p>
                      <div class="pilot-timeline__meta">
                        <span>Occurred ${escapeHtml(formatDateTime(receipt.receipt_timestamp))}</span>
                        <span>Provider execution ${escapeHtml(receipt.provider_execution_ref || "not provided")}</span>
                      </div>
                      ${
                        reconciliationRecords.length
                          ? `
                            <div class="pilot-list">
                              ${reconciliationRecords
                                .map(
                                  (record) => `
                                    <article class="pilot-subcard">
                                      <div class="pilot-subcard__header">
                                        <span>${escapeHtml(formatLabel(record.reconciliation_type))}</span>
                                        ${renderSignalBadge(record.status)}
                                      </div>
                                      <p>${escapeHtml(record.summary)}</p>
                                    </article>
                                  `
                                )
                                .join("")}
                            </div>
                            ${renderReconciliationChecks(reconciliationRecords)}
                          `
                          : `<p class="pilot-inline-note">No reconciliation records are currently linked to this receipt.</p>`
                      }
                    </article>
                  `;
                })
                .join("")}
            </div>
          `
          : `<p class="pilot-empty">No receipt has been ingested yet.</p>`
      }
    </article>
  `;
}

function renderProofExecutionAndReceipt(trace, action) {
  return `
    <section class="pilot-grid pilot-grid--three">
      ${renderProofPanel(trace)}
      ${renderExecutionPanel(trace, action)}
      ${renderReceiptPanel(trace, action)}
    </section>
  `;
}

function renderLinkedArtifacts(action, trace) {
  const latestProof = latestItem(trace.issued_proofs);
  const latestEscrow = latestItem(trace.escrow_records);
  const latestReceipt = latestItem(trace.receipts);
  const latestApproval = latestItem(trace.approvals);
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Linked artifacts</h3>
          <p>These are the main record identifiers already supported by the backend trace for this invoice payment.</p>
        </div>
      </div>
      <div class="pilot-grid pilot-grid--four">
        <div class="pilot-list__item">
          <h4>Latest proof</h4>
          <p>${renderOptionalCode(latestProof?.issued_proof_id)}</p>
        </div>
        <div class="pilot-list__item">
          <h4>Latest escrow</h4>
          <p>${renderOptionalCode(latestEscrow?.escrow_record_id)}</p>
        </div>
        <div class="pilot-list__item">
          <h4>Latest receipt</h4>
          <p>${renderOptionalCode(action.latest_receipt_id || latestReceipt?.receipt_id)}</p>
        </div>
        <div class="pilot-list__item">
          <h4>Latest approval request</h4>
          <p>${renderOptionalCode(latestApproval?.approval_request_id)}</p>
        </div>
        <div class="pilot-list__item">
          <h4>Linked evidence objects</h4>
          <p>${escapeHtml(trace.evidence_objects.length)} object(s)</p>
        </div>
        <div class="pilot-list__item">
          <h4>External intent id</h4>
          <p>${renderOptionalCode(action.external_action_intent_id)}</p>
        </div>
        <div class="pilot-list__item">
          <h4>Workflow binding</h4>
          <p>${escapeHtml(action.workflow_binding?.workflow_profile || "Not provided")}</p>
        </div>
        <div class="pilot-list__item">
          <h4>Client tags</h4>
          <p>${escapeHtml(action.client_tags.length ? action.client_tags.join(", ") : "No tags")}</p>
        </div>
        <div class="pilot-list__item">
          <h4>Trace export</h4>
          <p>Available from the action header</p>
        </div>
      </div>
    </section>
  `;
}

async function bindApprovalDecisionForms({ token, session, setStatus, refresh }) {
  for (const form of document.querySelectorAll("[data-approval-form]")) {
    for (const button of form.querySelectorAll("[data-decision]")) {
      button.addEventListener("click", async () => {
        const approvalRequestId = form.dataset.approvalRequestId;
        const decisionReason = form.querySelector('[name="decision_reason"]')?.value.trim() || null;
        if (button.dataset.decision === "reject" && !decisionReason) {
          setStatus("A decline reason is required before the action can be declined.", "error");
          return;
        }
        const confirmationMessage =
          button.dataset.decision === "approve"
            ? `Confirm approval for ${approvalRequestId}?`
            : `Confirm decline for ${approvalRequestId}? The current pilot does not reopen declined approval requests automatically.`;
        if (!window.confirm(confirmationMessage)) {
          return;
        }
        const payload = {
          decision: button.dataset.decision,
          decision_reason: decisionReason,
          evidence_object_ids: selectedEvidenceIds(form),
        };

        setStatus(`Submitting ${button.dataset.decision} decision...`);
        form.querySelectorAll("button").forEach((formButton) => {
          formButton.disabled = true;
        });
        try {
          await postJson(`/api/v1/approvals/${approvalRequestId}/decisions`, {
            token,
            payload,
          });
          setStatus(`Approval decision recorded for ${approvalRequestId}.`);
          await refresh();
        } catch (error) {
          setStatus(error.message || "Approval decision failed.", "error");
        } finally {
          form.querySelectorAll("button").forEach((formButton) => {
            formButton.disabled = false;
          });
        }
      });
    }

    const requestEvidenceButton = form.querySelector("[data-request-evidence]");
    requestEvidenceButton?.addEventListener("click", () => {
      const approvalRequestId = form.dataset.approvalRequestId;
      const uploadSelect = document.getElementById("upload-approval-request");
      const registerSelect = document.getElementById("register-approval-request");
      if (uploadSelect) {
        uploadSelect.value = approvalRequestId || "";
      }
      if (registerSelect) {
        registerSelect.value = approvalRequestId || "";
      }
      document.getElementById("evidence-actions")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      setStatus(
        "Approval remains pending. Use the evidence action forms below to upload or register supporting material.",
      );
    });
  }
}

async function bindEvidenceForms({ token, session, action, setStatus, refresh }) {
  const uploadForm = document.getElementById("evidence-upload-form");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const formData = new FormData(uploadForm);
        const metadata = parseOptionalJson(
          String(formData.get("evidence_metadata_json") || ""),
          "evidence metadata"
        );
        formData.set("tenant_id", action.tenant_id);
        formData.set("action_intent_record_id", action.action_intent_record_id);
        formData.set("evidence_metadata_json", JSON.stringify(metadata));
        if (!window.confirm("Upload this evidence and attach it to the current invoice payment action?")) {
          return;
        }

        setStatus("Uploading evidence...");
        uploadForm.querySelectorAll("button").forEach((button) => {
          button.disabled = true;
        });
        await postFormData("/api/v1/evidence/upload", {
          token,
          formData,
        });
        setStatus("Evidence uploaded successfully.");
        await refresh();
      } catch (error) {
        setStatus(error.message || "Evidence upload failed.", "error");
      } finally {
        uploadForm.querySelectorAll("button").forEach((button) => {
          button.disabled = false;
        });
      }
    });
  }

  const registerForm = document.getElementById("evidence-register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const formData = new FormData(registerForm);
        const metadata = parseOptionalJson(
          String(formData.get("evidence_metadata_json") || ""),
          "evidence metadata"
        );
        const payload = {
          tenant_id: action.tenant_id,
          action_intent_record_id: action.action_intent_record_id,
          approval_request_id: formData.get("approval_request_id") || null,
          evidence_type: String(formData.get("evidence_type") || "document"),
          storage_mode: formData.get("storage_mode"),
          storage_ref: String(formData.get("storage_ref") || ""),
          original_filename: String(formData.get("original_filename") || "") || null,
          media_type: String(formData.get("media_type") || "") || null,
          evidence_metadata: metadata,
          expires_at: String(formData.get("expires_at") || "") || null,
        };
        if (!window.confirm("Register this evidence reference for the current invoice payment action?")) {
          return;
        }

        setStatus("Registering external evidence...");
        registerForm.querySelectorAll("button").forEach((button) => {
          button.disabled = true;
        });
        await postJson("/api/v1/evidence/register", {
          token,
          payload,
        });
        setStatus("External evidence registered successfully.");
        await refresh();
      } catch (error) {
        setStatus(error.message || "Evidence registration failed.", "error");
      } finally {
        registerForm.querySelectorAll("button").forEach((button) => {
          button.disabled = false;
        });
      }
    });
  }
}

async function bindEvidenceAccessActions({ token, setStatus }) {
  for (const button of document.querySelectorAll("[data-evidence-action]")) {
    button.addEventListener("click", async () => {
      const evidenceObjectId = button.dataset.evidenceObjectId;
      const action = button.dataset.evidenceAction;
      const storageRef = button.dataset.storageRef;
      const originalFilename = button.dataset.originalFilename;

      try {
        if (action === "open-reference") {
          if (!storageRef) {
            throw new Error("evidence reference is missing a storage URI");
          }
          window.open(storageRef, "_blank", "noopener");
          return;
        }

        button.disabled = true;
        if (action === "preview-document") {
          const previewWindow = window.open("about:blank", "_blank");
          setStatus("Opening evidence preview...");
          await previewEvidenceContent({
            evidenceObjectId,
            token,
            previewWindow,
          });
          setStatus("");
          return;
        }

        if (action === "download-document") {
          setStatus("Downloading evidence...");
          await downloadEvidenceContent({
            evidenceObjectId,
            token,
            filename: originalFilename,
          });
          setStatus("");
        }
      } catch (error) {
        setStatus(error.message || "Evidence access failed.", "error");
      } finally {
        button.disabled = false;
      }
    });
  }
}

function renderAuditFeed(trace) {
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Audit trail</h3>
          <p>The current durable audit feed is strongest around receipt ingestion and reconciliation events, which are the most complete audit categories implemented today.</p>
        </div>
      </div>
      ${
        trace.audit_events.length
          ? `
            <div class="pilot-event-list">
              ${trace.audit_events
                .map(
                  (event) => `
                    <article class="pilot-event">
                      <div class="pilot-event__header">
                        <div>
                          <div class="pilot-timeline__eyebrow">${escapeHtml(event.event_category)}</div>
                          <h4>${escapeHtml(event.event_type)}</h4>
                        </div>
                        <span class="pilot-code">${escapeHtml(event.subject_id)}</span>
                      </div>
                      <p>Actor ${escapeHtml(event.actor_principal_type)} · ${escapeHtml(event.actor_principal_id)}</p>
                      <div class="pilot-timeline__meta">
                        <span>${escapeHtml(formatDateTime(event.created_at))}</span>
                        <span>${escapeHtml(event.subject_type)}</span>
                      </div>
                      <details>
                        <summary>Event payload</summary>
                        <pre class="pilot-pre">${escapeHtml(stringifyJson(event.event_payload))}</pre>
                      </details>
                    </article>
                  `
                )
                .join("")}
            </div>
          `
          : `<p class="pilot-empty">No audit events are currently linked to this action.</p>`
      }
    </section>
  `;
}

async function renderActionDetail({ token, session, contentEl, setStatus }) {
  const actionIntentRecordId = document.body.dataset.actionIntentRecordId;
  const refresh = async () => {
    const [action, trace, approvalRequests] = await Promise.all([
      fetchJson(`/api/v1/action-intents/${actionIntentRecordId}`, { token }),
      fetchJson(`/api/v1/audit/traces/${actionIntentRecordId}`, { token }),
      fetchJson("/api/v1/approvals", {
        token,
        params: {
          action_intent_record_id: actionIntentRecordId,
        },
      }),
    ]);

    const latestProof = latestItem(trace.issued_proofs);
    const latestEscrow = latestItem(trace.escrow_records);
    const latestReceipt = latestItem(trace.receipts);
    const evidenceDetails = await Promise.all(
      trace.evidence_objects.map((evidence) =>
        fetchJson(`/api/v1/evidence/${evidence.evidence_object_id}`, { token })
      )
    );

    contentEl.innerHTML = `
      ${renderHeader(action, trace, latestProof, latestEscrow, latestReceipt)}
      ${renderDecisionRationale(
        action,
        trace,
        latestProof,
        latestEscrow,
        latestReceipt,
        evidenceDetails
      )}
      ${renderOperatorWorkflow(action, trace, approvalRequests, session, latestProof)}
      ${renderTimeline(action, trace, latestProof, latestEscrow, latestReceipt)}
      ${renderApprovalProgress(trace, action)}
      ${renderProofExecutionAndReceipt(trace, action)}
      ${renderLinkedArtifacts(action, trace)}
      ${renderAuditFeed(trace)}
    `;

    const exportButton = document.getElementById("trace-export");
    if (exportButton) {
      exportButton.addEventListener("click", async () => {
        exportButton.disabled = true;
        try {
          await downloadTraceExport({
            actionIntentRecordId,
            token,
            suggestedName: `${sanitizeFilename(deriveInvoiceReference(action))}-${sanitizeFilename(
              actionIntentRecordId
            )}-audit-export.json`,
          });
        } finally {
          exportButton.disabled = false;
        }
      });
    }

    await bindApprovalDecisionForms({
      token,
      session,
      setStatus,
      refresh,
    });
    await bindEvidenceForms({
      token,
      session,
      action,
      setStatus,
      refresh,
    });
    await bindEvidenceAccessActions({
      token,
      setStatus,
    });
  };

  await refresh();
}

initializePilotShell({
  pageTitle: "Invoice Payment Action Detail",
  pageSubtitle:
    "Inspect one governed invoice payment action from intake through proof, release, receipt, and audit trace.",
  onReady: renderActionDetail,
});
