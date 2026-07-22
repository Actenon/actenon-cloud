# Pilot UI

This directory contains the narrow built-in customer UI for the managed invoice payment pilot.

It is intentionally small:

- one invoice payment action list
- one held and exceptions queue
- one invoice payment detail and trace view

It is not a broad admin console, not an internal infrastructure dashboard, and not the home of proof verification logic. Proof verification remains external through the separate verifier dependency or interface.

## Routes

- `/pilot/actions`
- `/pilot/review`
- `/pilot/actions/{action_intent_record_id}`

## Structure

- `routes.py` serves the HTML shell for each pilot page
- `static/actions-list.js` renders the invoice payment queue
- `static/review-queue.js` renders the held and exceptions queue
- `static/action-detail.js` renders the action detail and trace view
- `static/shared.js` contains shared API, formatting, auth-token, and state helpers
- `static/pilot.css` contains the minimal pilot styling

## Backend Dependencies

The pilot UI uses existing backend APIs rather than introducing a separate frontend backend layer.

Main dependencies:

- `GET /api/v1/auth/session`
- `GET /api/v1/action-intents`
- `GET /api/v1/usage/summary`
- `GET /api/v1/action-intents/{action_intent_record_id}`
- `GET /api/v1/evidence/{evidence_object_id}`
- `GET /api/v1/evidence/{evidence_object_id}/content`
- `GET /api/v1/audit/traces/{action_intent_record_id}`
- `GET /api/v1/audit/export?action_intent_record_id=...`
- `GET /api/v1/issuance/proofs`
- `POST /api/v1/approvals/{approval_request_id}/decisions`
- `POST /api/v1/evidence/upload`
- `POST /api/v1/evidence/register`

## Scope Notes

The current pilot UI is designed for trust and operability, not polish.

It should help a design partner:

- see all governed invoice payment actions
- see simple period usage truth for pilot reporting and ROI discussion
- classify each action at a glance by lifecycle, outcome, reviewability, and artifact readiness
- inspect one action end to end
- understand allow, hold, and block outcomes
- follow approval, evidence, proof, execution, and receipt stages separately
- review held actions that need approval or evidence intervention
- inspect proof, receipt, and linked artifact progression

The current operator workflow is intentionally narrow:

- review held actions in the dedicated review queue
- approve or decline only when the current token is assigned and permitted; the acting principal is derived from the authenticated session, not caller-supplied fields
- request evidence by moving directly into the existing evidence upload or register forms
- upload or register evidence under the authenticated session principal rather than caller-declared actor metadata
- preview or download filesystem-backed evidence and open external evidence references
- export the trace for manual follow-up outside the product
- see future usage-pricing candidates separately from blocked or refused prevention value

The current pilot UI does not persist operator notes, escalation ownership, or in-product follow-up status.
