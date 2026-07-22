# Pilot UI Completion Plan

## Purpose

This plan defines the minimum remaining UX work needed to make the existing pilot UI believable for a live managed invoice payment execution pilot.

It does not propose a broad frontend redesign. It assumes the current three-route shell stays in place:

- `/pilot/actions`
- `/pilot/review`
- `/pilot/actions/{action_intent_record_id}`

## Completion Standard

The pilot UI should be considered complete enough for a live design-partner pilot when an operator can:

- find the right invoice payment action quickly
- understand why it is allowed, held, or refused
- inspect the evidence and approval history behind that state
- take the supported review action without leaving the product
- export the trace when manual follow-up is required

## Phase 1: Close Trust-Surface Blockers

These items should land first because they affect whether the current surface feels truthful and operable.

### 1. Add Evidence Inspection To The Detail Page

Surface:

- extend the existing evidence section in `app/pilot_ui/static/action-detail.js`

Minimum UX:

- show a visible action for each evidence object:
  - download uploaded file
  - open external reference
  - indicate metadata-only evidence when no file exists

Backend dependency:

- add a controlled evidence retrieval endpoint for uploaded content

Acceptance criteria:

- an operator can open or download uploaded evidence from the detail page
- the page does not imply that every evidence object has downloadable content
- external and metadata-only evidence remain clearly labeled

### 2. Make External Evidence Registration Truthful

Surface:

- update the external evidence registration form in `app/pilot_ui/static/action-detail.js`

Minimum UX:

- add an `evidence_type` selector to the register form
- show the chosen type in the evidence section after save

Backend dependency:

- none beyond the existing `POST /api/v1/evidence/register` contract

Acceptance criteria:

- external evidence is no longer forced to `document`
- a registered attestation or external reference appears with the correct type in the trace

### 3. Make Approval Review Operable For The Policy Shape In Use

Surface:

- extend the approval decision section in `app/pilot_ui/static/action-detail.js`

Minimum UX:

- if the pilot uses explicit assignments only:
  - state that limit clearly when an approval is visible but not actionable
- if the pilot uses role-based eligibility:
  - expose the operator's eligible role claims
  - submit `claimed_role_ids` with approval decisions when needed

Backend dependency:

- approval payload already supports `claimed_role_ids`
- session or approval payload may need enough role context for the UI to act correctly

Acceptance criteria:

- no open approval request appears actionable in policy terms but blocked in UI terms
- the UI behavior matches the actual approval contract used by the pilot

### 4. Add A Chronological Transition Feed

Surface:

- extend the detail page with one ordered transition feed rather than only separate status panels

Minimum UX:

- show a chronological event rail for:
  - intake and contract decision
  - approval request creation and decisions
  - evidence upload or registration
  - proof issuance result
  - release and execution progression
  - receipt ingestion and reconciliation

Backend dependency:

- enrich `GET /api/v1/audit/traces/{action_intent_record_id}` with fuller transition records
- or add those events to the audit feed used by the detail page

Acceptance criteria:

- an operator can explain how the action moved from intake to current state without reading raw JSON
- the event rail is backed by stored records, not only inferred state labels

## Phase 2: Make The Review Queue Easier To Run

These items are important next, but they are not as fundamental as the trust blockers above.

### 5. Expand Queue Triage Controls

Surface:

- extend `app/pilot_ui/static/actions-list.js`
- extend `app/pilot_ui/static/review-queue.js`

Minimum UX:

- add filters for the most useful current state axes already supported by the list API:
  - approval state
  - evidence state
  - execution state
  - receipt state
- add clearer review-driver labels where needed

Backend dependency:

- mostly none; `GET /api/v1/action-intents` already supports these filters
- optional queue-summary enrichments if expiry or urgency needs to be shown cleanly

Acceptance criteria:

- an operator can isolate approval work, evidence work, and downstream exceptions without reading every row

### 6. Decide Whether Follow-Up Tracking Stays Outside The Product

Surface:

- current review queue already warns that follow-up ownership and notes are not persisted

Decision point:

- if the managed pilot will use external runbooks, leave this out of the product for now
- if multiple customer operators will share the queue directly, add a minimal in-product handoff surface

Possible minimum UX if included:

- note
- owner
- external case reference
- follow-up status

Backend dependency:

- would require a new narrow persistence surface

## Phase 3: Low-Risk Usability Improvements

These help polish the pilot without changing the product boundary.

### 7. Queue Convenience

- quick trace export from queue rows
- copy record IDs from linked artifacts
- optional pagination or sort controls if pilot volume increases

### 8. Detail Page Convenience

- collapse or expand raw JSON sections more deliberately
- highlight latest proof, escrow, and receipt records more strongly
- make reconciliation failures easier to scan when many checks exist

## Build Order Recommendation

1. Evidence inspection and truthful evidence registration
2. Approval operability for the approval policy shape the pilot actually uses
3. Chronological transition feed on the detail page
4. Queue triage filters and review-driver clarity
5. Optional follow-up tracking only if the pilot needs in-product shared queue ownership

## Recommended Delivery Shape

Keep the implementation narrow:

- no new product area
- no generic admin console
- no broad UI rewrite
- no verifier logic

The most credible path is to finish the trust surface inside the existing action detail and queue views.
