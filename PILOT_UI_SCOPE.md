# Pilot UI Scope

## Purpose

This document defines the minimum viable customer-operable UI for the invoice payment execution pilot.

It intentionally stays narrow:

- one managed single-tenant pilot
- one invoice payment workflow family
- one operator console, not a broad platform suite

## UI Goal

The pilot UI should let a design partner do these things well:

- observe each invoice payment action
- identify held and exception cases quickly
- inspect lifecycle state
- inspect proof and receipt progression
- understand why an action was allowed, held, or blocked
- take review actions when workflow intervention is required

## Current Minimum UI Shape

The current minimum UI is a browser-based single-tenant operator console with three primary views and a small number of focused embedded review panels.

### 1. Invoice Payment Queue

Primary purpose:

- show every in-scope invoice payment action for the pilot tenant

Route:

- `/pilot/actions`

Minimum columns:

- action identifier
- external reference
- tenant or account scope
- supplier or payee reference when available
- amount and currency
- current state
- allow or hold or block outcome
- proof status
- receipt status
- last updated timestamp

Minimum filters:

- outcome
- decision state
- approval state
- evidence state
- execution state
- receipt state
- external reference
- created or updated time

Minimum operator outcomes from this view:

- open the action detail view
- identify which actions need human attention now

### 2. Held And Exceptions Queue

Primary purpose:

- separate reviewable held actions from blocked final outcomes and manual follow-up cases

Route:

- `/pilot/review`

Minimum sections:

- review now
- manual follow-up
- blocked final outcomes

Minimum operator outcomes from this view:

- open an action that needs approval or evidence work now
- avoid spending time on blocked outcomes that are not reversible in the current pilot
- identify exceptions that still require manual follow-up outside the current backend transitions

### 3. Invoice Payment Detail And Trace

Primary purpose:

- give one coherent, operator-readable record for a single invoice payment action from intake through receipt

Route:

- `/pilot/actions/{action_intent_record_id}`

Recommended sections:

- action summary
- decision rationale
- lifecycle timeline
- approval progression
- evidence received summary
- proof progression
- release and escrow state
- receipt progression and reconciliation panel
- audit event feed

Minimum action summary fields:

- action intent record id
- external reference
- finance action class
- amount and currency
- source or destination account references
- requested by
- created at

Minimum decision explanation fields:

- contract validation status
- decision state
- decision reason
- matched rule id
- evaluation trace

Minimum lifecycle state fields:

- approval state
- evidence state
- execution state
- receipt state
- latest receipt id

### 4. Embedded Review Panels

These can be modal, drawer, or tabbed panels inside the action detail view rather than separate screens.

Required review panels:

- submit approval decision
- upload or register evidence
- export the full action trace

Visible-but-read-only lifecycle panels:

- proof progression
- release and escrow progression
- receipt progression and reconciliation

These stages matter to operator trust, but they do not need first-class mutation controls in the minimum pilot UI.

## Components Required

The UI only needs a small component set.

Required components:

- state badge set for decision, approval, evidence, execution, receipt, proof, and escrow state
- action summary header
- held and exceptions queue
- decision rationale card
- lifecycle timeline or ordered state rail
- approval timeline
- evidence list
- proof progression panel
- release or escrow progression panel
- receipt progression panel
- reconciliation summary card
- audit event list
- export button

## API Dependencies

### Existing APIs The UI Can Rely On

- `GET /api/v1/auth/session`
- `GET /api/v1/action-intents`
- `GET /api/v1/action-intents/{action_intent_record_id}`
- `POST /api/v1/approvals/{approval_request_id}/decisions`
- `POST /api/v1/evidence/register`
- `POST /api/v1/evidence/upload`
- `GET /api/v1/issuance/proofs`
- `GET /api/v1/audit/traces/{action_intent_record_id}`
- `GET /api/v1/audit/export?action_intent_record_id=...`

### Minimum Remaining API Gap For The UI

The remaining strongly recommended addition, if uploaded evidence must be reviewed in the browser, is:

- a controlled evidence retrieval surface for uploaded evidence payloads

## Current Detail Experience

The current restored pilot detail view should prioritize trust over density. It should answer four operator questions clearly:

- what state the invoice payment is in now
- why it is allowed, held, or blocked
- whether proof and release progressed
- whether a receipt confirms or challenges the prior control decision

The current detail experience is therefore expected to show:

- a decision rationale panel
- a six-step lifecycle timeline
- an approval progression timeline
- an evidence summary
- proof progression cards
- receipt progression cards with reconciliation summaries
- linked artifact identifiers
- audit feed and trace export

## User Flows In Scope

### Flow A: Observe Payment Status

1. Open invoice payment queue.
2. Filter to one payment or one review state.
3. Open action detail.
4. Read decision explanation and lifecycle state.

### Flow B: Resolve Approval Requirement

1. Open an action with `approval_state=pending`.
2. Inspect action summary, decision trace, and linked evidence.
3. Submit approve or reject.
4. Confirm updated approval and action state.

### Flow C: Resolve Evidence Requirement

1. Open an action with `evidence_state=pending`.
2. Upload or register evidence.
3. Confirm evidence state becomes satisfied or remains pending.
4. Return to action detail for next control step.

### Flow D: Review Proof And Receipt Progression

1. Open an action whose controls are satisfied.
2. Inspect proof status and any release or escrow state that already exists.
3. Confirm whether execution moved forward or stopped.
4. Confirm whether a receipt has been ingested and reconciled.

### Flow E: Export Full Trace

1. Open an action that needs review outside the product.
2. Export the action trace JSON.
3. Use the export in finance, audit, or provider follow-up as needed.

## Explicitly Out Of Scope

The pilot UI should not include:

- cross-tenant navigation
- generic admin surfaces
- policy authoring
- service-principal management
- internal service monitoring
- proof verification logic
- policy editing screens
- metrics dashboards
- infrastructure health dashboards
- full evidence management portal
- batch operation console
- speculative analytics views

## Scope Conclusion

The minimum viable UI is not a dashboard program. It is a focused operator console for one invoice payment workflow, with:

- one queue
- one detail and trace view
- a few narrow review panels

That is the right UI size for the pilot and the current backend maturity.
