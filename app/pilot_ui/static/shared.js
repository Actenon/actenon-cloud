const TOKEN_STORAGE_KEY = "action-control-plane.pilot-token";

function asText(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }
  return String(value);
}

export function escapeHtml(value) {
  return asText(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function formatLabel(value) {
  if (!value) {
    return "Not provided";
  }
  return String(value).replaceAll("_", " ");
}

export function formatDateTime(value) {
  if (!value) {
    return "Not recorded";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return escapeHtml(value);
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export function formatMoney(amountMinor, currency) {
  if (amountMinor === null || amountMinor === undefined) {
    return "Not provided";
  }
  try {
    const formatted = new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
    }).format(Number(amountMinor) / 100);
    return currency ? formatted : `${formatted} (currency not provided)`;
  } catch {
    const unit = currency ? ` ${currency}` : "";
    return `${Number(amountMinor).toLocaleString()} minor units${unit}`;
  }
}

export function renderBadge(value, tone = "neutral") {
  const label = formatLabel(value);
  return `<span class="pilot-badge pilot-badge--${tone}">${escapeHtml(label)}</span>`;
}

export function renderStateBadge(value) {
  return renderBadge(value, "neutral");
}

export function currentPrincipal(session) {
  return {
    principalType: session?.principal_type || "",
    principalId: session?.principal_id || "",
  };
}

export function getTenantAccess(session, tenantId) {
  return (session?.tenant_access || []).find((tenantAccess) => tenantAccess.tenant_id === tenantId);
}

export function hasTenantPermission(session, tenantId, permission) {
  const tenantAccess = getTenantAccess(session, tenantId);
  return Boolean(tenantAccess?.permissions?.includes(permission));
}

export function stringifyJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

export function derivePayeeReference(record) {
  const metadata = record.action_intent_payload?.metadata || {};
  return (
    metadata.vendor_name ||
    metadata.vendor_id ||
    metadata.payee_reference ||
    metadata.invoice_number ||
    record.destination_account_ref ||
    record.finance_index?.destination_account_ref ||
    "Not provided"
  );
}

export function deriveInvoiceReference(record) {
  const metadata = record.action_intent_payload?.metadata || {};
  return (
    record.external_reference ||
    metadata.invoice_number ||
    metadata.invoice_id ||
    record.external_action_intent_id ||
    record.action_intent_record_id
  );
}

export function deriveOutcome(record, latestProofStatus = null) {
  if (!record) {
    return {
      label: "unknown",
      tone: "neutral",
      reason: "Action state is not available.",
    };
  }
  if (
    record.decision_state === "deny" ||
    record.decision_state === "structurally_non_executable"
  ) {
    return {
      label: "blocked",
      tone: "blocked",
      reason: record.decision_reason || "The action was blocked during intake.",
    };
  }
  if (record.approval_state === "pending") {
    return {
      label: "held",
      tone: "held",
      reason: "The action is waiting for required approval.",
    };
  }
  if (record.evidence_state === "pending") {
    return {
      label: "held",
      tone: "held",
      reason: "The action is waiting for required evidence.",
    };
  }
  if (record.approval_state === "expired" || record.evidence_state === "expired") {
    return {
      label: "held",
      tone: "held",
      reason: "A required approval or evidence item expired before execution.",
    };
  }
  if (latestProofStatus === "failed" || latestProofStatus === "rejected") {
    return {
      label: "held",
      tone: "held",
      reason: "Proof issuance did not complete successfully.",
    };
  }
  if (
    record.execution_state === "not_requested" ||
    record.execution_state === "capability_held" ||
    record.execution_state === "capability_released" ||
    record.execution_state === "dispatch_requested" ||
    record.execution_state === "dispatch_confirmed"
  ) {
    return {
      label: "held",
      tone: "held",
      reason: record.decision_reason || "The action is still inside the governed release flow.",
    };
  }
  return {
    label: "allowed",
    tone: "allowed",
    reason: record.decision_reason || "The action cleared the required control steps.",
  };
}

export function deriveLifecycleStage(record, latestProofStatus = null) {
  if (!record) {
    return {
      label: "Unknown lifecycle",
      tone: "neutral",
      detail: "Action state is not available.",
    };
  }
  if (
    record.decision_state === "deny" ||
    record.decision_state === "structurally_non_executable"
  ) {
    return {
      label: "Refused at intake",
      tone: "blocked",
      detail: "The action stopped during contract or policy intake.",
    };
  }
  if (record.approval_state === "pending") {
    return {
      label: "Waiting for approval",
      tone: "held",
      detail: "Required approval is still open for this invoice payment.",
    };
  }
  if (record.approval_state === "rejected") {
    return {
      label: "Approval declined",
      tone: "held",
      detail: "A recorded approval decline stopped in-product progress.",
    };
  }
  if (record.approval_state === "expired") {
    return {
      label: "Approval expired",
      tone: "held",
      detail: "An approval window expired before the action could continue.",
    };
  }
  if (record.approval_state === "canceled") {
    return {
      label: "Approval canceled",
      tone: "held",
      detail: "The approval workflow was canceled before completion.",
    };
  }
  if (record.evidence_state === "pending") {
    return {
      label: "Waiting for evidence",
      tone: "held",
      detail: "Supporting evidence is still required before release can continue.",
    };
  }
  if (record.evidence_state === "expired") {
    return {
      label: "Evidence expired",
      tone: "held",
      detail: "A required evidence item expired before the action could continue.",
    };
  }
  if (record.evidence_state === "canceled") {
    return {
      label: "Evidence canceled",
      tone: "held",
      detail: "The evidence requirement was canceled before completion.",
    };
  }
  if (latestProofStatus === "requested") {
    return {
      label: "Awaiting proof issuance",
      tone: "held",
      detail: "A proof request exists, but no issued proof is recorded yet.",
    };
  }
  if (latestProofStatus === "failed" || latestProofStatus === "rejected") {
    return {
      label: "Proof exception",
      tone: "held",
      detail: "Proof issuance did not complete successfully.",
    };
  }
  if (record.receipt_state === "reconciled") {
    return {
      label: "Receipt reconciled",
      tone: "allowed",
      detail: "A receipt was ingested and reconciled against the linked records.",
    };
  }
  if (record.receipt_state === "received" || record.receipt_state === "indexed") {
    return {
      label: "Receipt received",
      tone: "held",
      detail: "A receipt exists, but reconciliation is not complete yet.",
    };
  }
  if (record.execution_state === "failure_observed") {
    return {
      label: "Execution failure observed",
      tone: "blocked",
      detail: "A downstream result indicates failure for this action.",
    };
  }
  if (record.execution_state === "result_observed") {
    return {
      label: "Result observed",
      tone: "allowed",
      detail: "A downstream result was recorded and the receipt trail is still settling.",
    };
  }
  if (
    record.execution_state === "capability_released" ||
    record.execution_state === "dispatch_requested" ||
    record.execution_state === "dispatch_confirmed"
  ) {
    return {
      label: "Awaiting receipt",
      tone: "held",
      detail: "Capability moved forward, but no final receipt is recorded yet.",
    };
  }
  if (record.execution_state === "capability_held") {
    return {
      label: latestProofStatus === "issued" ? "Ready for release" : "Held before release",
      tone: "held",
      detail:
        latestProofStatus === "issued"
          ? "Required checks passed, but the action is still held before release."
          : "The action has not moved past the managed release hold yet.",
    };
  }
  if (record.execution_state === "revoked") {
    return {
      label: "Release revoked",
      tone: "blocked",
      detail: "Capability release was revoked before completion.",
    };
  }
  if (record.execution_state === "quarantined") {
    return {
      label: "Release quarantined",
      tone: "held",
      detail: "Capability release is quarantined pending follow-up.",
    };
  }
  if (record.execution_state === "expired") {
    return {
      label: "Release expired",
      tone: "held",
      detail: "Capability release expired before a final result was recorded.",
    };
  }
  if (record.execution_state === "not_requested") {
    return {
      label: "Accepted into control plane",
      tone: "held",
      detail: "The action is recorded, but no release path has started yet.",
    };
  }
  return {
    label: formatLabel(record.execution_state || "unknown"),
    tone: "neutral",
    detail: "The current lifecycle state is recorded on the action.",
  };
}

export function deriveReceiptAvailability(record) {
  if (!record) {
    return {
      label: "Receipt unknown",
      tone: "neutral",
      detail: "Receipt status is not available.",
    };
  }
  if (record.receipt_state === "reconciled") {
    return {
      label: "Receipt reconciled",
      tone: "allowed",
      detail: "A receipt and reconciliation record are available.",
    };
  }
  if (record.receipt_state === "received" || record.receipt_state === "indexed") {
    return {
      label: "Receipt available",
      tone: "held",
      detail: "A receipt exists, but reconciliation is not complete yet.",
    };
  }
  if (
    record.decision_state === "deny" ||
    record.decision_state === "structurally_non_executable"
  ) {
    return {
      label: "No receipt expected",
      tone: "neutral",
      detail: "The action stopped before execution could begin.",
    };
  }
  return {
    label: "Receipt pending",
    tone: "neutral",
    detail: "No receipt has been ingested yet.",
  };
}

export function deriveReviewDisposition(record, latestProofStatus = null) {
  const outcome = deriveOutcome(record, latestProofStatus);
  if (outcome.label === "blocked") {
    return {
      bucket: "blocked",
      label: "Blocked final",
      tone: "blocked",
      reason: outcome.reason,
      nextStep: "Read-only outcome",
    };
  }
  if (
    record.approval_state === "pending" &&
    (record.evidence_state === "pending" || record.evidence_state === "expired")
  ) {
    return {
      bucket: "reviewable",
      label: "Approval and evidence review",
      tone: "held",
      reason: "This held action still needs approval review and supporting evidence.",
      nextStep: "Approve, decline, or request evidence",
    };
  }
  if (record.approval_state === "pending") {
    return {
      bucket: "reviewable",
      label: "Approval review",
      tone: "held",
      reason: "An approver can review this held action now.",
      nextStep: "Approve or decline",
    };
  }
  if (record.evidence_state === "pending" || record.evidence_state === "expired") {
    return {
      bucket: "reviewable",
      label: "Evidence review",
      tone: "held",
      reason: "Supporting evidence is missing or expired.",
      nextStep: "Request evidence",
    };
  }
  if (
    record.approval_state === "rejected" ||
    record.approval_state === "expired" ||
    record.approval_state === "canceled"
  ) {
    return {
      bucket: "follow_up",
      label: "Approval exception",
      tone: "held",
      reason: "The current pilot backend does not reopen rejected or expired approvals.",
      nextStep: "Manual follow-up",
    };
  }
  if (latestProofStatus === "failed" || latestProofStatus === "rejected") {
    return {
      bucket: "follow_up",
      label: "Proof exception",
      tone: "held",
      reason: "Proof issuance did not complete successfully.",
      nextStep: "Manual follow-up",
    };
  }
  if (record.execution_state === "failure_observed") {
    return {
      bucket: "follow_up",
      label: "Execution exception",
      tone: "held",
      reason: "The latest recorded execution result is a failure.",
      nextStep: "Manual follow-up",
    };
  }
  return {
    bucket: "observe",
    label: "Observe only",
    tone: "neutral",
    reason: outcome.reason,
    nextStep: "Monitor lifecycle",
  };
}

export function deriveOperatorStatus(record, latestProofStatus = null) {
  const disposition = deriveReviewDisposition(record, latestProofStatus);
  if (disposition.bucket === "reviewable") {
    return {
      bucket: disposition.bucket,
      label: "Reviewable now",
      tone: "held",
      detail: disposition.reason,
      nextStep: disposition.nextStep,
      finality: "open",
    };
  }
  if (disposition.bucket === "blocked") {
    return {
      bucket: disposition.bucket,
      label: "Final refusal",
      tone: "blocked",
      detail: "Blocked or structurally refused. This outcome is read only in the current pilot.",
      nextStep: disposition.nextStep,
      finality: "final",
    };
  }
  if (disposition.bucket === "follow_up") {
    return {
      bucket: disposition.bucket,
      label: "Manual follow-up",
      tone: "held",
      detail: disposition.reason,
      nextStep: disposition.nextStep,
      finality: "open",
    };
  }
  if (record?.receipt_state === "reconciled") {
    return {
      bucket: "observe",
      label: "Final recorded",
      tone: "allowed",
      detail: "A reconciled receipt is linked and this action is read only in the pilot UI.",
      nextStep: "Read-only outcome",
      finality: "final",
    };
  }
  const lifecycle = deriveLifecycleStage(record, latestProofStatus);
  if (
    lifecycle.label === "Awaiting receipt" ||
    lifecycle.label === "Receipt received" ||
    lifecycle.label === "Result observed" ||
    lifecycle.label === "Ready for release"
  ) {
    return {
      bucket: "observe",
      label: "Monitor in progress",
      tone: "neutral",
      detail: lifecycle.detail,
      nextStep: "Monitor lifecycle",
      finality: "observe",
    };
  }
  return {
    bucket: "observe",
    label: "Observe only",
    tone: "neutral",
    detail: "No review action is currently exposed. Open detail to inspect or export the trace.",
    nextStep: "Monitor lifecycle",
    finality: "observe",
  };
}

export function getStoredToken() {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
}

export function setStoredToken(token) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function requestJson(path, { token, params, method = "GET", headers = {}, body } = {}) {
  const url = new URL(path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const response = await window.fetch(url, {
    method,
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body,
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchJson(path, { token, params } = {}) {
  return requestJson(path, { token, params });
}

export async function fetchBlob(path, { token, params } = {}) {
  const url = new URL(path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const response = await window.fetch(url, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }
  return {
    blob: await response.blob(),
    contentType: response.headers.get("content-type") || "application/octet-stream",
  };
}

export async function postJson(path, { token, payload, params } = {}) {
  return requestJson(path, {
    token,
    params,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
}

export async function postFormData(path, { token, formData, params } = {}) {
  return requestJson(path, {
    token,
    params,
    method: "POST",
    body: formData,
  });
}

export function sanitizeFilename(value) {
  const cleaned = String(value || "")
    .trim()
    .replaceAll(/[^a-zA-Z0-9._-]+/g, "-")
    .replaceAll(/-+/g, "-")
    .replaceAll(/^-|-$/g, "");
  return cleaned || "actenon-cloud";
}

function downloadBlob({ blob, filename }) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

export async function downloadTraceExport({
  actionIntentRecordId,
  token,
  suggestedName,
}) {
  const payload = await fetchJson("/api/v1/audit/export", {
    token,
    params: { action_intent_record_id: actionIntentRecordId },
  });
  downloadBlob({
    blob: new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    }),
    filename: suggestedName || `${actionIntentRecordId}-trace.json`,
  });
}

export async function downloadEvidenceContent({ evidenceObjectId, token, filename }) {
  const { blob } = await fetchBlob(`/api/v1/evidence/${evidenceObjectId}/content`, {
    token,
    params: { disposition: "attachment" },
  });
  downloadBlob({
    blob,
    filename: filename || `${evidenceObjectId}.bin`,
  });
}

export async function previewEvidenceContent({ evidenceObjectId, token, previewWindow = null }) {
  const { blob, contentType } = await fetchBlob(`/api/v1/evidence/${evidenceObjectId}/content`, {
    token,
    params: { disposition: "inline" },
  });
  const previewBlob =
    blob.type || !contentType ? blob : new Blob([blob], { type: contentType });
  const url = window.URL.createObjectURL(previewBlob);
  if (previewWindow && !previewWindow.closed) {
    previewWindow.location.href = url;
  } else {
    window.open(url, "_blank", "noopener");
  }
  window.setTimeout(() => {
    window.URL.revokeObjectURL(url);
  }, 60_000);
}

export function latestByActionIntent(items) {
  const grouped = new Map();
  for (const item of items || []) {
    const actionIntentRecordId = item.action_intent_record_id;
    if (!actionIntentRecordId) {
      continue;
    }
    const existing = grouped.get(actionIntentRecordId);
    if (!existing) {
      grouped.set(actionIntentRecordId, item);
      continue;
    }
    const currentTime = Date.parse(item.updated_at || item.created_at || "");
    const existingTime = Date.parse(existing.updated_at || existing.created_at || "");
    if (Number.isNaN(existingTime) || currentTime > existingTime) {
      grouped.set(actionIntentRecordId, item);
    }
  }
  return grouped;
}

function renderShell(pageTitle, pageSubtitle) {
  return `
    <section class="pilot-card pilot-banner">
      <div class="pilot-banner__row">
        <div>
          <h2>${escapeHtml(pageTitle)}</h2>
          <p class="pilot-inline-note">${escapeHtml(pageSubtitle)}</p>
        </div>
      </div>
      <form id="token-form" class="pilot-form">
        <div class="pilot-field">
          <label for="token-input">Operator bearer token</label>
          <input id="token-input" name="token" type="password" autocomplete="off" placeholder="Paste pilot bearer token">
        </div>
        <button class="pilot-button pilot-button--primary" type="submit">Use token</button>
        <button id="clear-token" class="pilot-button pilot-button--secondary" type="button">Clear token</button>
      </form>
      <div id="session-panel" class="pilot-stack"></div>
    </section>
    <section id="page-status"></section>
    <section id="page-content" class="pilot-stack"></section>
  `;
}

function renderSessionPanel(session) {
  const tenantOptions = (session.tenant_access || [])
    .map(
      (tenantAccess) => `
        <option value="${escapeHtml(tenantAccess.tenant_id)}">${escapeHtml(tenantAccess.tenant_id)}</option>
      `
    )
    .join("");
  const tenantSelector = tenantOptions
    ? `
      <div class="pilot-field">
        <label for="tenant-select">Pilot tenant</label>
        <select id="tenant-select">${tenantOptions}</select>
      </div>
    `
    : "";
  return `
    <div class="pilot-card">
      <div class="pilot-banner__row">
        <div>
          <strong>${escapeHtml(session.display_name)}</strong>
          <p class="pilot-inline-note">
            ${escapeHtml(session.principal_type)} · ${escapeHtml(session.token_kind)} token ·
            expires ${escapeHtml(formatDateTime(session.expires_at))}
          </p>
        </div>
        ${tenantSelector}
      </div>
    </div>
  `;
}

function renderMissingTenantMessage() {
  return `
    <div class="pilot-card pilot-card--warning">
      <h3>No tenant context available</h3>
      <p>
        This pilot UI expects a tenant-scoped operator token. The current session does not expose
        a pilot tenant, so the invoice payment views cannot load customer data yet.
      </p>
    </div>
  `;
}

function setStatus(message = "", tone = "neutral") {
  const status = document.getElementById("page-status");
  if (!status) {
    return;
  }
  if (!message) {
    status.innerHTML = "";
    return;
  }
  const className = tone === "error" ? "pilot-error" : "pilot-inline-note";
  status.innerHTML = `<section class="pilot-card"><p class="${className}">${escapeHtml(message)}</p></section>`;
}

export async function initializePilotShell({ pageTitle, pageSubtitle, onReady }) {
  const app = document.getElementById("pilot-app");
  app.insertAdjacentHTML("beforeend", renderShell(pageTitle, pageSubtitle));

  const tokenInput = document.getElementById("token-input");
  const tokenForm = document.getElementById("token-form");
  const clearTokenButton = document.getElementById("clear-token");
  const sessionPanel = document.getElementById("session-panel");
  const pageContent = document.getElementById("page-content");

  async function activateSession(token) {
    if (!token) {
      sessionPanel.innerHTML = "";
      pageContent.innerHTML = "";
      setStatus("Paste a valid pilot bearer token to load invoice payment data.");
      return;
    }

    setStatus("Loading pilot session...");
    try {
      const session = await fetchJson("/api/v1/auth/session", { token });
      setStoredToken(token);
      sessionPanel.innerHTML = renderSessionPanel(session);
      const tenantSelect = document.getElementById("tenant-select");
      if (!tenantSelect) {
        pageContent.innerHTML = renderMissingTenantMessage();
        setStatus("");
        return;
      }

      const loadForTenant = async () => {
        setStatus("Loading invoice payment data...");
        pageContent.innerHTML = "";
        try {
          await onReady({
            token,
            session,
            tenantId: tenantSelect.value,
            contentEl: pageContent,
            setStatus,
          });
          setStatus("");
        } catch (error) {
          pageContent.innerHTML = "";
          setStatus(error.message || "The pilot page failed to load.", "error");
        }
      };

      tenantSelect.addEventListener("change", loadForTenant);
      await loadForTenant();
    } catch (error) {
      clearStoredToken();
      sessionPanel.innerHTML = "";
      pageContent.innerHTML = "";
      setStatus(error.message || "The pilot token could not be validated.", "error");
    }
  }

  tokenInput.value = getStoredToken();

  tokenForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await activateSession(tokenInput.value.trim());
  });

  clearTokenButton.addEventListener("click", () => {
    clearStoredToken();
    tokenInput.value = "";
    sessionPanel.innerHTML = "";
    pageContent.innerHTML = "";
    setStatus("Pilot token cleared.");
  });

  await activateSession(tokenInput.value.trim());
}
