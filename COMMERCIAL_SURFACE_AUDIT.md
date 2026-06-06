# Commercial Surface Audit

## Purpose

This document audits the current commercial and buyer-facing surface of Actenon Cloud for the invoice payment execution wedge.

It separates:

- technical strength
- buyer readability
- design-partner clarity
- proposal readiness
- early GTM readiness

It does not redesign the product and does not treat the current repo as production-ready.

## Documents Reviewed

- `README.md`
- `SHIP_STATUS.md`
- `CONTROL_PLANE_RELEASE_READINESS.md`
- `BLOCKERS.md`
- `DESIGN_PARTNER_PILOT_OVERVIEW.md`
- `PILOT_SCOPE_AND_BOUNDARIES.md`
- `PILOT_ARCHITECTURE.md`
- `PILOT_OPERATOR_JOURNEY.md`
- `PILOT_SUCCESS_METRICS.md`
- `PILOT_DELIVERY_PLAN.md`
- `PILOT_RISK_REGISTER.md`
- `PILOT_LIMITATIONS.md`
- `PILOT_EXECUTIVE_BRIEF.md`
- `PILOT_OFFER_ONE_PAGER.md`
- `PILOT_COMMERCIAL_PROPOSAL_TEMPLATE.md`
- `PILOT_STATEMENT_OF_WORK_TEMPLATE.md`
- `PILOT_SCOPE_AND_PRICING.md`
- `PILOT_BUYER_FAQ.md`
- `PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md`

Additional note:

- `OPEN_SOURCE_BOUNDARY.md` is not present in the repo; the open kernel versus paid control-plane boundary is instead described in `README.md`, `docs/OPEN_KERNEL_DEPENDENCY_MODEL.md`, and the pilot docs

## Executive Assessment

### Technical Surface

Strong.

For the invoice payment execution wedge, the repo already has:

- a real end-to-end governance workflow
- a credible pilot package
- explicit limitation and blocker docs
- real APIs, state transitions, receipts, and audit traces

### Commercial Surface

Improved, but still partial.

Compared with the earlier state, the repo now has real commercial scaffolding:

- a one-pager
- a proposal template
- a statement-of-work template
- a buyer FAQ
- a pilot security summary
- a scope and pricing framework

That is enough to support serious design-partner conversations.

It is not yet enough for repeatable outreach or broad GTM execution because the current materials are still stronger in pilot packaging than in buyer positioning.

## What Is Already Commercially Strong

### 1. The wedge is narrow and credible

The invoice payment execution wedge is commercially strong because it is:

- specific
- understandable
- tied to a real finance control problem
- consistent with the actual implementation

This is much stronger than a generic “workflow platform” or vague “AI platform” story.

### 2. The open kernel versus paid control plane split is clear

The repo clearly explains the open kernel boundary and the paid control-plane value above it.

That is commercially important because it creates a believable upgrade story from the open layer to the commercial layer without hiding the boundary.

### 3. The pilot is honest

The current commercial surface is unusually credible because it says plainly:

- what works
- what is simulated
- what does not execute yet
- why pilot readiness is Amber rather than Green

This is a trust asset in early design-partner conversations.

### 4. The proposal surface is now real

The repo now contains a practical offer package:

- `PILOT_OFFER_ONE_PAGER.md`
- `PILOT_COMMERCIAL_PROPOSAL_TEMPLATE.md`
- `PILOT_STATEMENT_OF_WORK_TEMPLATE.md`
- `PILOT_BUYER_FAQ.md`
- `PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md`

That means the commercial surface is no longer just technical planning. It is now capable of supporting an actual pilot conversation.

### 5. The pilot story is operationally specific

The buyer-facing and operator-facing materials describe:

- how a payment is proposed
- when approvals and evidence are needed
- how a payment is allowed or refused
- how receipts are viewed afterward

That makes the pilot legible to an operations team, not only to engineers.

## What Is Too Technical

### README.md is still engineer-first

`README.md` still reads more like a repository and implementation summary than a buyer-led introduction.

It explains:

- repo structure
- current implementation slices
- acceptance gates

It does not lead with:

- buyer problem
- operational pain
- why invoice payment execution is the right first commercial wedge

### Ship and readiness docs are useful but not sales-friendly

`SHIP_STATUS.md`, `CONTROL_PLANE_RELEASE_READINESS.md`, and `BLOCKERS.md` are strong diligence docs.

They are not good first-touch commercial docs because they read like internal engineering truth documents, not buyer narratives.

### Internal system nouns still appear too early

The pilot surface still depends on terms such as:

- Action Intent
- proof issuance
- capability escrow
- kernel-aligned receipt

These are accurate terms, but many buyers will understand:

- payment proposal
- control decision
- release approval
- execution receipt

more quickly than the system-native vocabulary.

### Architecture is still component-led

`PILOT_ARCHITECTURE.md` is technically sound, but buyer readability is still limited because it starts from components and boundaries instead of starting from the change in the customer’s payment workflow.

## What Is Unclear To A Buyer

### 1. Ideal customer profile

The repo still does not say clearly which design partners are best suited for this pilot.

What is still unclear:

- size and maturity of the finance function
- expected payment volume
- ERP or payable-system maturity
- tolerance for a controlled pilot with simulated release

### 2. Pilot commitment level

The materials now describe a proposal and a statement of work, but they still do not fully answer:

- how long a typical pilot should run
- how many invoice payments are enough to validate the wedge
- how many customer stakeholders are needed
- how much internal customer effort is expected week to week

### 3. Buyer outcome language

The success metrics are good, but they are still more operational than economic.

A buyer may still ask:

- what pain gets reduced fastest
- what manual ambiguity disappears
- what kind of review burden improves
- what kind of error prevention matters most

### 4. What happens after a successful pilot

The docs say the next step is production hardening, which is honest.

What is still unclear is the commercial shape of that transition:

- what changes first
- what stays pilot-only
- how the open kernel versus paid control plane decision evolves

## What Is Missing For A Real Pilot Proposal

The repo is much closer now, but a few important pieces are still missing or incomplete for a serious pilot proposal:

- a clearly named ideal customer profile
- a qualification checklist for whether a prospect is a good fit
- a buyer-oriented mutual success plan
- a weekly pilot operating cadence
- a final pilot readout template
- a stronger economic or ROI framing
- a clearer open kernel to paid control plane conversion explanation

## What Is Missing For Early GTM Readiness

The biggest early GTM gaps are now:

### 1. Buyer persona framing

The materials are better for technical sponsors than for:

- AP leaders
- controllers
- CFO sponsors
- security reviewers

### 2. Repeatable outreach language

There is now a one-pager, but the repo still lacks a crisp outreach narrative that can be reused across prospects without walking them through the full doc set.

### 3. Qualification discipline

There is still no single document that says:

- who is a good fit
- who is a bad fit
- what conditions make the pilot likely to fail

### 4. Conversion story from the open kernel to paid control plane

The open kernel boundary is clear technically, but the commercial articulation is still light.

The repo still needs a sharper explanation of:

- why an open-kernel user would pay for the control plane
- when they should do so
- what value the commercial layer adds beyond the open kernel

### 5. ROI framing

The repo does not yet have a simple ROI or budget-justification narrative for invoice payment execution.

`PILOT_SCOPE_AND_PRICING.md` exists, but it is intentionally a framework rather than approved pricing, and there is no supporting business case yet.

## File-By-File Commercial Assessment

| File | Current Commercial Value | Main Remaining Issue |
| --- | --- | --- |
| `README.md` | Strong technical credibility | Too repo-centric for first-touch buyers |
| `DESIGN_PARTNER_PILOT_OVERVIEW.md` | Good wedge articulation | Still slightly system-led |
| `PILOT_SCOPE_AND_BOUNDARIES.md` | Strong scope discipline | Not buyer-oriented enough |
| `PILOT_ARCHITECTURE.md` | Good diligence asset | Too technical for non-technical sponsors |
| `PILOT_OPERATOR_JOURNEY.md` | Strong operator clarity | Less useful for executive buyers |
| `PILOT_SUCCESS_METRICS.md` | Strong pilot evaluation | Weak economic framing |
| `PILOT_DELIVERY_PLAN.md` | Good delivery discipline | Needs clearer sponsor-level commitment framing |
| `PILOT_RISK_REGISTER.md` | Strong honesty | Better for diligence than outreach |
| `PILOT_LIMITATIONS.md` | Strong trust asset | Needs a companion ROI narrative |
| `PILOT_EXECUTIVE_BRIEF.md` | Helpful summary | Still not fully executive in tone |
| `PILOT_OFFER_ONE_PAGER.md` | Strong new offer summary | Still missing ICP and buyer personas |
| `PILOT_COMMERCIAL_PROPOSAL_TEMPLATE.md` | Strong new proposal scaffold | Still template-only |
| `PILOT_STATEMENT_OF_WORK_TEMPLATE.md` | Strong delivery scaffold | Still needs deal-specific cadence and outputs |
| `PILOT_SCOPE_AND_PRICING.md` | Honest packaging framework | No approved pricing or entitlement model |
| `PILOT_BUYER_FAQ.md` | Good early objections handling | Needs companion qualification guide |
| `PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md` | Good early diligence asset | Still not a full security review packet |

## Bottom Line

The current commercial surface is no longer weak. It is now credible for a serious design-partner pilot conversation around invoice payment execution.

The biggest remaining issue is not absence of materials. It is that the commercial layer is still stronger in:

- technical honesty
- pilot structure
- delivery discipline

than it is in:

- buyer targeting
- outreach efficiency
- ROI framing
- open kernel to paid control-plane conversion language
