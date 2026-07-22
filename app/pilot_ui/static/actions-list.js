import {
  deriveInvoiceReference,
  deriveLifecycleStage,
  deriveOperatorStatus,
  deriveOutcome,
  derivePayeeReference,
  deriveReceiptAvailability,
  escapeHtml,
  fetchJson,
  formatDateTime,
  formatMoney,
  initializePilotShell,
  latestByActionIntent,
  renderBadge,
  renderStateBadge,
} from "./shared.js";

function renderUsageSummary(report) {
  if (!report) {
    return "";
  }
  const totals = report.totals || {};
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Current reporting period usage</h3>
          <p>
            Metering only for the current pilot. Proved and allowed actions are the future
            per-action usage candidates. Blocked or refused actions remain visible as prevention
            value and are not usage-billed.
          </p>
        </div>
      </div>
      <div class="pilot-inline-note">
        Reporting period: ${escapeHtml(formatDateTime(report.period_start))} to
        ${escapeHtml(formatDateTime(report.period_end))}
      </div>
      <section class="pilot-kpis">
        <article class="pilot-kpi">
          <div class="pilot-kpi__label">Submitted</div>
          <div class="pilot-kpi__value">${totals.submitted_actions || 0}</div>
        </article>
        <article class="pilot-kpi">
          <div class="pilot-kpi__label">Proved and Allowed</div>
          <div class="pilot-kpi__value">${totals.billable_proved_and_allowed_actions || 0}</div>
        </article>
        <article class="pilot-kpi">
          <div class="pilot-kpi__label">Blocked / Refused</div>
          <div class="pilot-kpi__value">${totals.blocked_or_refused_actions || 0}</div>
        </article>
        <article class="pilot-kpi">
          <div class="pilot-kpi__label">Reviewed</div>
          <div class="pilot-kpi__value">${totals.reviewed_actions || 0}</div>
        </article>
        <article class="pilot-kpi">
          <div class="pilot-kpi__label">Receipts Linked</div>
          <div class="pilot-kpi__value">${totals.receipt_linked_actions || 0}</div>
        </article>
      </section>
    </section>
  `;
}

function renderQueueMetrics(actions, proofsByAction) {
  const totals = {
    total: actions.length,
    blocked: 0,
    held: 0,
    allowed: 0,
    reviewable: 0,
    finalRecorded: 0,
  };

  for (const action of actions) {
    const latestProof = proofsByAction.get(action.action_intent_record_id);
    const outcome = deriveOutcome(action, latestProof?.status);
    const operatorStatus = deriveOperatorStatus(action, latestProof?.status);
    totals[outcome.label] += 1;
    if (operatorStatus.bucket === "reviewable") {
      totals.reviewable += 1;
    }
    if (operatorStatus.label === "Final recorded") {
      totals.finalRecorded += 1;
    }
  }

  return `
    <section class="pilot-kpis">
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Actions</div>
        <div class="pilot-kpi__value">${totals.total}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Allowed</div>
        <div class="pilot-kpi__value">${totals.allowed}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Held</div>
        <div class="pilot-kpi__value">${totals.held}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Blocked / Refused</div>
        <div class="pilot-kpi__value">${totals.blocked}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Reviewable Now</div>
        <div class="pilot-kpi__value">${totals.reviewable}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Final Recorded</div>
        <div class="pilot-kpi__value">${totals.finalRecorded}</div>
      </article>
    </section>
  `;
}

function queueOperatorFilterValue(operatorStatus) {
  if (operatorStatus.bucket === "reviewable") {
    return "reviewable";
  }
  if (operatorStatus.bucket === "follow_up") {
    return "follow_up";
  }
  if (operatorStatus.finality === "final") {
    return "final";
  }
  return "observe";
}

function queueRow(action, proofStatus) {
  const outcome = deriveOutcome(action, proofStatus);
  const lifecycle = deriveLifecycleStage(action, proofStatus);
  const operatorStatus = deriveOperatorStatus(action, proofStatus);
  const receiptAvailability = deriveReceiptAvailability(action);
  const currentStates = [
    renderStateBadge(action.decision_state),
    renderStateBadge(action.approval_state),
    renderStateBadge(action.evidence_state),
    renderStateBadge(action.execution_state),
  ].join("");
  const sourceAccount = action.source_account_ref || "unknown source";
  const destinationAccount = action.destination_account_ref || "unknown destination";
  const visibleOutcomeLabel = outcome.label === "blocked" ? "blocked / refused" : outcome.label;
  const proofBadge = proofStatus
    ? renderStateBadge(proofStatus)
    : renderBadge("proof not requested", "neutral");

  return `
    <tr
      data-href="/pilot/actions/${escapeHtml(action.action_intent_record_id)}"
      data-review-bucket="${escapeHtml(operatorStatus.bucket)}"
      data-finality="${escapeHtml(operatorStatus.finality)}"
      data-outcome-tone="${escapeHtml(outcome.tone)}"
    >
      <td>
        <div class="pilot-cell-stack">
          <strong>${escapeHtml(deriveInvoiceReference(action))}</strong>
          <div class="pilot-inline-note">${escapeHtml(sourceAccount)} to ${escapeHtml(destinationAccount)}</div>
          <div class="pilot-inline-note pilot-code">${escapeHtml(action.action_intent_record_id)}</div>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          <strong>${escapeHtml(derivePayeeReference(action))}</strong>
          <div class="pilot-inline-note">${escapeHtml(action.external_reference || "No external reference")}</div>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          <strong>${escapeHtml(formatMoney(action.amount_minor, action.currency))}</strong>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          ${renderBadge(lifecycle.label, lifecycle.tone)}
          <div class="pilot-inline-note">${escapeHtml(lifecycle.detail)}</div>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          ${renderBadge(visibleOutcomeLabel, outcome.tone)}
          <div class="pilot-inline-note">${escapeHtml(outcome.reason)}</div>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          ${renderBadge(operatorStatus.label, operatorStatus.tone)}
          <div class="pilot-inline-note">${escapeHtml(operatorStatus.detail)}</div>
          <div class="pilot-inline-note"><strong>Next step:</strong> ${escapeHtml(operatorStatus.nextStep)}</div>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          <div class="pilot-badges">${currentStates}</div>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          <div class="pilot-badges">
            ${proofBadge}
            ${renderBadge(receiptAvailability.label, receiptAvailability.tone)}
            ${renderBadge("trace export in detail", "neutral")}
          </div>
          <div class="pilot-inline-note">${escapeHtml(receiptAvailability.detail)}</div>
        </div>
      </td>
      <td>
        <div class="pilot-cell-stack">
          <strong>${escapeHtml(formatDateTime(action.updated_at))}</strong>
        </div>
      </td>
    </tr>
  `;
}

function renderQueue(actions, proofsByAction, useFilterBody = false) {
  if (!actions.length) {
    return `
      <section class="pilot-card">
        <h3>No invoice payment actions found</h3>
        <p class="pilot-empty">
          This pilot tenant does not have any governed invoice payment actions yet for the
          selected workflow filter.
        </p>
      </section>
    `;
  }

  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Invoice payment queue</h3>
          <p>Classify outcome, lifecycle, reviewability, and artifact readiness before opening the full action trace.</p>
        </div>
      </div>
      <div class="pilot-table-wrap">
        <table class="pilot-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Supplier or payee</th>
              <th>Amount</th>
              <th>Lifecycle</th>
              <th>Outcome</th>
              <th>Reviewability</th>
              <th>Control state</th>
              <th>Artifacts</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody${useFilterBody ? ' id="queue-body"' : ""}>
            ${actions
              .map((action) =>
                queueRow(action, proofsByAction.get(action.action_intent_record_id)?.status || null)
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function attachRowNavigation() {
  for (const row of document.querySelectorAll("[data-href]")) {
    row.addEventListener("click", () => {
      window.location.assign(row.dataset.href);
    });
  }
}

function attachQueueFilters(actions, proofsByAction) {
  const searchInput = document.getElementById("queue-search");
  const outcomeFilter = document.getElementById("queue-outcome");
  const operatorFilter = document.getElementById("queue-reviewability");
  const body = document.getElementById("queue-body");

  if (!searchInput || !outcomeFilter || !operatorFilter || !body) {
    return;
  }

  const renderFiltered = () => {
    const searchText = searchInput.value.trim().toLowerCase();
    const outcomeText = outcomeFilter.value;
    const operatorText = operatorFilter.value;
    const filtered = actions.filter((action) => {
      const proofStatus = proofsByAction.get(action.action_intent_record_id)?.status || null;
      const outcome = deriveOutcome(action, proofStatus);
      const operatorStatus = deriveOperatorStatus(action, proofStatus);
      const searchable = [
        deriveInvoiceReference(action),
        action.external_reference,
        action.external_action_intent_id,
        action.destination_account_ref,
        derivePayeeReference(action),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      const matchesSearch = !searchText || searchable.includes(searchText);
      const matchesOutcome = !outcomeText || outcome.label === outcomeText;
      const matchesOperator =
        !operatorText || queueOperatorFilterValue(operatorStatus) === operatorText;
      return matchesSearch && matchesOutcome && matchesOperator;
    });
    body.innerHTML = filtered
      .map((action) =>
        queueRow(action, proofsByAction.get(action.action_intent_record_id)?.status || null)
      )
      .join("");
    attachRowNavigation();
  };

  searchInput.addEventListener("input", renderFiltered);
  outcomeFilter.addEventListener("change", renderFiltered);
  operatorFilter.addEventListener("change", renderFiltered);
}

function renderFilterBar() {
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Queue filters</h3>
          <p>Filter within the current pilot tenant by outcome or operator review status.</p>
        </div>
        <div class="pilot-badges">
          <a class="pilot-button pilot-button--secondary" href="/pilot/review">Open held and exceptions queue</a>
        </div>
      </div>
      <div class="pilot-form">
        <div class="pilot-field">
          <label for="queue-search">Search by invoice, external reference, or payee</label>
          <input id="queue-search" type="search" placeholder="invoice, payee, or external reference">
        </div>
        <div class="pilot-field">
          <label for="queue-outcome">Outcome</label>
          <select id="queue-outcome">
            <option value="">All outcomes</option>
            <option value="allowed">Allowed</option>
            <option value="held">Held</option>
            <option value="blocked">Blocked / refused</option>
          </select>
        </div>
        <div class="pilot-field">
          <label for="queue-reviewability">Operator status</label>
          <select id="queue-reviewability">
            <option value="">All operator states</option>
            <option value="reviewable">Reviewable now</option>
            <option value="follow_up">Manual follow-up</option>
            <option value="final">Final outcomes</option>
            <option value="observe">Observe only</option>
          </select>
        </div>
      </div>
    </section>
  `;
}

function renderQueueWithFilterIds(actions, proofsByAction) {
  return renderQueue(actions, proofsByAction, true);
}

async function renderActionList({ token, tenantId, contentEl }) {
  const [actions, proofs, usageSummary] = await Promise.all([
    fetchJson("/api/v1/action-intents", {
      token,
      params: {
        tenant_id: tenantId,
        workflow_key: "payments.standard",
      },
    }),
    fetchJson("/api/v1/issuance/proofs", {
      token,
      params: {
        tenant_id: tenantId,
      },
    }),
    fetchJson("/api/v1/usage/summary", {
      token,
      params: {
        tenant_id: tenantId,
        workflow_key: "payments.standard",
      },
    }).catch(() => null),
  ]);

  const proofsByAction = latestByActionIntent(proofs);
  contentEl.innerHTML = `
    ${renderUsageSummary(usageSummary)}
    ${renderQueueMetrics(actions, proofsByAction)}
    ${renderFilterBar()}
    ${renderQueueWithFilterIds(actions, proofsByAction)}
  `;
  attachRowNavigation();
  attachQueueFilters(actions, proofsByAction);
}

initializePilotShell({
  pageTitle: "Invoice Payment Actions",
  pageSubtitle:
    "Use this queue to classify governed invoice payment actions quickly, then open the full trace when a row needs review.",
  onReady: renderActionList,
});
