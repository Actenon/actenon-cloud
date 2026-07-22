import {
  deriveInvoiceReference,
  deriveLifecycleStage,
  deriveOperatorStatus,
  derivePayeeReference,
  deriveReceiptAvailability,
  deriveReviewDisposition,
  escapeHtml,
  fetchJson,
  formatDateTime,
  formatMoney,
  hasTenantPermission,
  initializePilotShell,
  latestByActionIntent,
  renderBadge,
  renderStateBadge,
} from "./shared.js";

function reviewRow(action, proofStatus) {
  const disposition = deriveReviewDisposition(action, proofStatus);
  const operatorStatus = deriveOperatorStatus(action, proofStatus);
  const lifecycle = deriveLifecycleStage(action, proofStatus);
  const receiptAvailability = deriveReceiptAvailability(action);
  const currentStates = [
    renderStateBadge(action.decision_state),
    renderStateBadge(action.approval_state),
    renderStateBadge(action.evidence_state),
    renderStateBadge(action.execution_state),
  ].join("");
  const proofBadge = proofStatus
    ? renderStateBadge(proofStatus)
    : renderBadge("proof not requested", "neutral");

  return `
    <tr
      data-href="/pilot/actions/${escapeHtml(action.action_intent_record_id)}"
      data-review-bucket="${escapeHtml(operatorStatus.bucket)}"
      data-finality="${escapeHtml(operatorStatus.finality)}"
    >
      <td>
        <div class="pilot-cell-stack">
          <strong>${escapeHtml(deriveInvoiceReference(action))}</strong>
          <div class="pilot-inline-note">${escapeHtml(derivePayeeReference(action))}</div>
          <div class="pilot-inline-note pilot-code">${escapeHtml(action.action_intent_record_id)}</div>
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
          ${renderBadge(operatorStatus.label, operatorStatus.tone)}
          <div class="pilot-inline-note">${escapeHtml(disposition.reason)}</div>
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
          <strong>${escapeHtml(disposition.nextStep)}</strong>
          <div class="pilot-inline-note">${escapeHtml(operatorStatus.detail)}</div>
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

function attachRowNavigation() {
  for (const row of document.querySelectorAll("[data-href]")) {
    row.addEventListener("click", () => {
      window.location.assign(row.dataset.href);
    });
  }
}

function groupActions(actions, proofsByAction) {
  const groups = {
    reviewable: [],
    followUp: [],
    blocked: [],
  };

  for (const action of actions) {
    const proofStatus = proofsByAction.get(action.action_intent_record_id)?.status || null;
    const disposition = deriveReviewDisposition(action, proofStatus);
    if (disposition.bucket === "reviewable") {
      groups.reviewable.push(action);
    } else if (disposition.bucket === "follow_up") {
      groups.followUp.push(action);
    } else if (disposition.bucket === "blocked") {
      groups.blocked.push(action);
    }
  }
  return groups;
}

function renderQueueSection({ title, description, emptyMessage, bucketKey, actions, proofsByAction }) {
  if (!actions.length) {
    return `
      <section class="pilot-card">
        <div class="pilot-section-header">
          <div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(description)}</p>
          </div>
        </div>
        <p class="pilot-empty">${escapeHtml(emptyMessage)}</p>
      </section>
    `;
  }

  return `
    <section class="pilot-card" data-review-section="${escapeHtml(bucketKey)}">
      <div class="pilot-section-header">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(description)}</p>
        </div>
      </div>
      <div class="pilot-table-wrap">
        <table class="pilot-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Amount</th>
              <th>Lifecycle</th>
              <th>Reviewability</th>
              <th>Control state</th>
              <th>Artifacts</th>
              <th>Next step</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            ${actions
              .map((action) =>
                reviewRow(action, proofsByAction.get(action.action_intent_record_id)?.status || null)
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderMetrics(groups) {
  return `
    <section class="pilot-kpis">
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Review Now</div>
        <div class="pilot-kpi__value">${groups.reviewable.length}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Manual Follow-up</div>
        <div class="pilot-kpi__value">${groups.followUp.length}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Blocked / Refused</div>
        <div class="pilot-kpi__value">${groups.blocked.length}</div>
      </article>
      <article class="pilot-kpi">
        <div class="pilot-kpi__label">Total Exceptions</div>
        <div class="pilot-kpi__value">${groups.reviewable.length + groups.followUp.length + groups.blocked.length}</div>
      </article>
    </section>
  `;
}

function renderPermissionSummary(session, tenantId) {
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Operator authority</h3>
          <p>This queue separates reviewable held actions from manual follow-up cases and final refusals. Open the detail view to approve, decline, request evidence, or export the trace.</p>
        </div>
      </div>
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
        ${renderBadge("final refusals are read only", "blocked")}
      </div>
      <p class="pilot-inline-note">
        The current pilot backend does not persist operator notes, escalation ownership, or follow-up status. Use the trace export and runbook outside the product for those cases.
      </p>
    </section>
  `;
}

function renderFilterBar() {
  return `
    <section class="pilot-card">
      <div class="pilot-section-header">
        <div>
          <h3>Review queue filters</h3>
          <p>Use this page to separate live operator work from blocked/refused outcomes and manual follow-up items.</p>
        </div>
        <div class="pilot-badges">
          <a class="pilot-button pilot-button--secondary" href="/pilot/actions">Open full action queue</a>
        </div>
      </div>
      <div class="pilot-form">
        <div class="pilot-field">
          <label for="review-search">Search by invoice, external reference, or payee</label>
          <input id="review-search" type="search" placeholder="invoice, payee, or external reference">
        </div>
        <div class="pilot-field">
          <label for="review-bucket">Queue section</label>
          <select id="review-bucket">
            <option value="">All sections</option>
            <option value="reviewable">Review now</option>
            <option value="follow_up">Manual follow-up</option>
            <option value="blocked">Blocked / refused</option>
          </select>
        </div>
      </div>
    </section>
  `;
}

function searchTextForAction(action) {
  return [
    deriveInvoiceReference(action),
    action.external_reference,
    action.external_action_intent_id,
    action.destination_account_ref,
    derivePayeeReference(action),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function renderSections(actions, proofsByAction, bucketFilter, searchText) {
  const matching = actions.filter((action) => {
    const proofStatus = proofsByAction.get(action.action_intent_record_id)?.status || null;
    const disposition = deriveReviewDisposition(action, proofStatus);
    const matchesBucket = !bucketFilter || disposition.bucket === bucketFilter;
    const matchesSearch = !searchText || searchTextForAction(action).includes(searchText);
    return disposition.bucket !== "observe" && matchesBucket && matchesSearch;
  });

  const groups = groupActions(matching, proofsByAction);

  return `
    ${renderMetrics(groups)}
    ${renderQueueSection({
      title: "Review now",
      description:
        "These invoice payment actions are held, and the current pilot backend exposes an operator action now.",
      emptyMessage: "No held actions currently need direct operator review.",
      bucketKey: "reviewable",
      actions: groups.reviewable,
      proofsByAction,
    })}
    ${renderQueueSection({
      title: "Manual follow-up",
      description:
        "These actions have a recorded exception, but the current pilot backend does not complete the next transition inside the product yet.",
      emptyMessage: "No manual follow-up items are currently present.",
      bucketKey: "follow_up",
      actions: groups.followUp,
      proofsByAction,
    })}
    ${renderQueueSection({
      title: "Blocked final / refused",
      description:
        "These outcomes were stopped by policy or structure and are shown for visibility, not for in-product reversal.",
      emptyMessage: "No blocked or refused final outcomes are currently in scope for this tenant.",
      bucketKey: "blocked",
      actions: groups.blocked,
      proofsByAction,
    })}
  `;
}

async function renderReviewQueue({ token, tenantId, session, contentEl }) {
  const [actions, proofs] = await Promise.all([
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
  ]);

  const proofsByAction = latestByActionIntent(proofs);
  contentEl.innerHTML = `
    ${renderPermissionSummary(session, tenantId)}
    ${renderFilterBar()}
    <div id="review-sections"></div>
  `;

  const reviewSections = document.getElementById("review-sections");
  const searchInput = document.getElementById("review-search");
  const bucketSelect = document.getElementById("review-bucket");

  const rerender = () => {
    const bucketFilter = bucketSelect?.value || "";
    const searchText = searchInput?.value.trim().toLowerCase() || "";
    reviewSections.innerHTML = renderSections(actions, proofsByAction, bucketFilter, searchText);
    attachRowNavigation();
  };

  searchInput?.addEventListener("input", rerender);
  bucketSelect?.addEventListener("change", rerender);
  rerender();
}

initializePilotShell({
  pageTitle: "Invoice Payment Review Queue",
  pageSubtitle:
    "Use this queue to separate reviewable held actions from manual follow-up cases and blocked/refused final outcomes.",
  onReady: renderReviewQueue,
});
