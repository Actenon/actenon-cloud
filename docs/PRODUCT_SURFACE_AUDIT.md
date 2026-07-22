# Product Surface Audit

## Purpose

This document audits the current pilot product surface for the invoice payment execution workflow and identifies the minimum missing UX required for a believable live pilot experience.

It stays within the current repo boundary:

- one managed single-tenant pilot
- one invoice payment workflow family
- one narrow operator console
- no verifier logic in this repo
- no broad platform redesign

## Files Inspected

Frontend and pilot UI:

- `app/pilot_ui/routes.py`
- `app/pilot_ui/static/actions-list.js`
- `app/pilot_ui/static/review-queue.js`
- `app/pilot_ui/static/action-detail.js`
- `app/pilot_ui/static/shared.js`
- `app/pilot_ui/static/pilot.css`

Supporting APIs and services:

- `app/api/auth.py`
- `app/api/action_intents.py`
- `app/api/approvals.py`
- `app/api/evidence.py`
- `app/api/audit.py`
- `app/api/issuance.py`
- `app/services/action_intents.py`
- `app/services/approvals.py`
- `app/services/evidence.py`
- `app/services/audit.py`
- `app/services/issuance.py`
- `app/services/receipts.py`

Supporting docs and tests:

- `app/pilot_ui/README.md`
- `PILOT_UI_SCOPE.md`
- `docs/APPROVAL_WORKFLOW.md`
- `docs/EVIDENCE_MODEL.md`
- `tests/integration/test_pilot_ui.py`

## Audit Summary

The current repo already contains a real pilot UI, not just a placeholder shell.

It is already credible for:

- browsing the invoice payment queue
- opening one action and reading the current control outcome
- following approval, proof, execution, receipt, and reconciliation state at a summary level
- submitting approval decisions for explicitly assigned approvers
- uploading or registering evidence
- exporting the full trace JSON bundle

It is not yet a complete customer-operable trust surface for a live pilot because four important gaps remain:

1. uploaded evidence can be attached but not inspected in-product
2. the external evidence registration flow does not let the operator classify evidence type correctly
3. role-based approval eligibility is visible in the backend contract but not operable in the UI
4. the detail page explains stages well, but it still lacks a complete chronological transition feed backed by durable events across the full workflow

## Existing Pilot UI Surfaces

### 1. Pilot Shell

Existing behavior:

- token entry form stored in browser local storage
- `GET /api/v1/auth/session` bootstrap for operator session
- tenant selector driven by session scope

Truth:

- this is an engineering-pilot auth shell, not a customer-grade login experience
- for a managed pilot, it is usable enough, but it should not be mistaken for finished auth UX

### 2. Invoice Payment Queue

Route:

- `/pilot/actions`

Existing behavior:

- action KPIs for total, allowed, held, and blocked
- searchable queue
- outcome filter
- row navigation into detail view
- queue columns for action, account scope, payee, amount, outcome, current state, proof, receipt, and updated time

Truth:

- this is already a useful operator queue for a small pilot
- current filtering is intentionally light and stays client-side

### 3. Held And Exceptions Queue

Route:

- `/pilot/review`

Existing behavior:

- separates actions into `review now`, `manual follow-up`, and `blocked final`
- displays review status, current state, and next step
- search and section filtering
- operator authority summary based on tenant permissions

Truth:

- this is a believable review queue for the happy path
- it is strongest for approval-pending and evidence-pending actions
- it still relies on external runbooks for manual follow-up cases

### 4. Invoice Payment Detail And Trace

Route:

- `/pilot/actions/{action_intent_record_id}`

Existing behavior:

- action header with outcome, proof, receipt, and key metadata
- decision rationale section
- six-step lifecycle timeline
- approval progression section
- operator review section
- proof, execution, and receipt panels
- linked artifact summary
- audit trail panel
- trace export button

Truth:

- the detail page is already the strongest product surface in the repo
- it explains allow, hold, and refuse outcomes more clearly than the queue pages
- it is already close to the minimum pilot detail experience

## Goal-By-Goal Audit

| Pilot goal | Current status | What is true today |
| --- | --- | --- |
| Inspect each action | Mostly complete | Queue and detail pages already let an operator browse actions and open one full record. |
| Understand allow, hold, and refuse outcomes | Mostly complete | The queue and detail page derive current outcome from stored decision, approval, evidence, proof, execution, and receipt state. |
| Inspect approval progression | Partially complete | Approval requests and decisions are shown clearly, but the UI only works directly for explicit assignment flows. |
| Inspect evidence progression | Partially complete | Evidence metadata is shown and new evidence can be added, but uploaded files cannot be retrieved in-product. |
| Understand every state transition | Partially complete | The UI has a strong synthesized lifecycle view, but the durable audit feed is still sparse outside receipt and reconciliation events. |
| Export the trace | Complete for pilot needs | The detail page can export full trace JSON today. |
| Operate the review queue | Partially complete | Approval and evidence happy paths are workable, but exception handling still falls back to external follow-up. |

## Must-Have Missing Pilot UX

These are the smallest gaps that should be closed before the pilot UI can be described as a believable live operating surface.

### 1. Evidence Retrieval And Inspection

Current gap:

- evidence objects are listed from metadata only
- the detail page explicitly says browser-safe file retrieval is not implemented
- `GET /api/v1/evidence/{evidence_object_id}` returns metadata, not file content

Why this is must-have:

- an approver cannot meaningfully trust an evidence-backed hold resolution without opening the evidence itself
- metadata-only evidence review is not enough for invoice payment exceptions in a live pilot

Minimum acceptable pilot surface:

- a safe download or temporary access action from the detail page for uploaded evidence
- clear handling for `filesystem`, `external_uri`, and `inline_metadata_only` evidence modes

### 2. Correct External Evidence Classification

Current gap:

- the upload form lets the operator choose `evidence_type`
- the external evidence registration form does not
- `action-detail.js` currently posts `evidence_type: "document"` for every external registration

Why this is must-have:

- it can misclassify externally registered evidence in the trace
- it can prevent the evidence record from matching a policy requirement that expects a different evidence type
- it weakens trust in the evidence history even when the operator is using the supported register path

Minimum acceptable pilot surface:

- let the operator choose evidence type when registering external evidence
- show the chosen type clearly in the evidence list and linked review state

### 3. Role-Based Approval Operability

Current gap:

- approval requests can carry `eligible_role_ids`
- the backend decision API accepts `claimed_role_ids`
- the current UI does not expose role claims and only supports explicit principal assignment cleanly
- the detail page already admits that role-based approval matching is not exposed in the current session payload

Why this is must-have:

- a live pilot cannot claim a complete approval review surface if some valid approval requests are visible but not actionable
- this is especially important if the pilot policy uses role eligibility instead of explicit principal assignment

Minimum acceptable pilot surface:

- either expose enough role context to submit `claimed_role_ids` correctly
- or explicitly constrain the pilot to assigned-principal approval policies and state that limit in product and docs

### 4. Full Transition Provenance

Current gap:

- the UI shows current state very well
- the audit feed itself is strongest around receipt ingestion and reconciliation
- earlier transitions across intake, approval creation, evidence arrival, proof issuance outcome, and release progression are not presented as one durable chronological event stream

Why this is must-have:

- the stated pilot promise is governed invoice payment traceability
- design partners need to see not only where the action is now, but how it got there

Minimum acceptable pilot surface:

- one chronological transition rail on the detail page
- backed by durable trace or audit records rather than only synthesized current-state summaries

## Nice-To-Have Pilot UX

These would improve day-to-day use, but they are not the minimum blockers for a believable live pilot.

### Queue Triage Enhancements

- expose more filters already supported by `GET /api/v1/action-intents`
- add urgency cues such as approval expiry or stale age
- add quick export and copy-id actions from queue rows

### Manual Follow-Up Tracking

- operator note
- assignee or owner
- external case reference
- simple follow-up status

This would help shared queue operations, but the current managed pilot can still rely on runbooks outside the product.

### Convenience And Density Improvements

- queue sorting and pagination
- saved filters
- raw proof payload drawer
- richer receipt or reconciliation drill-down defaults

## Backend And API Dependencies

### Already Sufficient

These current APIs are enough for the existing three-screen pilot shell:

- `GET /api/v1/auth/session`
- `GET /api/v1/action-intents`
- `GET /api/v1/action-intents/{action_intent_record_id}`
- `GET /api/v1/approvals`
- `POST /api/v1/approvals/{approval_request_id}/decisions`
- `GET /api/v1/audit/traces/{action_intent_record_id}`
- `GET /api/v1/audit/export?action_intent_record_id=...`
- `POST /api/v1/evidence/upload`
- `POST /api/v1/evidence/register`
- `GET /api/v1/issuance/proofs`

### Still Needed For A Complete Trust Surface

- a controlled evidence retrieval endpoint for uploaded content
- richer transition history in the audit or trace response, or a dedicated transition feed in the existing trace contract
- enough session or approval metadata to make role-based approvals operable when `eligible_role_ids` are in use

## Audit Conclusion

The current pilot UI is already materially better than a placeholder.

It does not need a broad redesign. The existing three routes are the right shape for the invoice payment pilot:

- `/pilot/actions`
- `/pilot/review`
- `/pilot/actions/{action_intent_record_id}`

The work left is narrower than a frontend rebuild. The believable live-pilot finish line is:

- make evidence inspectable
- make external evidence classification truthful
- make approval review operable for the approval policy shape the pilot actually uses
- make full transition provenance visible in one trustworthy detail view
