# GTM Asset Gap Map

## Purpose

This document maps the minimum GTM asset stack needed for early design-partner conversations around the invoice payment execution pilot.

It separates:

- assets that are already usable
- assets that exist but still need refinement
- assets that are still missing

It is intentionally scoped to current pilot readiness:

- internal development readiness: Green
- design-partner pilot readiness: Amber
- production deployment readiness: Red

## Rule For This Asset Stack

The current GTM goal is not broad market launch.

The current GTM goal is narrower:

- support early design-partner conversations
- qualify whether a prospect is a strong fit for the invoice payment execution pilot
- support a controlled pilot proposal if fit is confirmed

## Asset Status Legend

- `Sufficient`: usable now for early design-partner motion
- `Partial`: useful now, but still needs refinement before repeatable use
- `Missing`: should be created in a future GTM pass

## Must-Have Assets For First Design-Partner Outreach

| Asset | Current Source | Status | Why This Status |
| --- | --- | --- | --- |
| Buyer problem statement | `BUYER_PROBLEM.md` | Sufficient | Clearly states the invoice-payment-control pain in plain language. |
| Wedge narrative | `WEDGE_NARRATIVE.md` | Sufficient | Explains why invoice payment execution is the first wedge and why it is commercially credible. |
| Value hypothesis | `DESIGN_PARTNER_VALUE_HYPOTHESIS.md` | Sufficient | Gives a bounded hypothesis without inventing outcomes. |
| Commercial baseline | `COMMERCIAL_BASELINE.md` | Sufficient | Anchors the motion to current implementation truth and current maturity. |
| Executive summary for the pilot | `PILOT_EXECUTIVE_BRIEF.md` | Partial | Good summary, but still a bit compact for repeatable first-touch use. |
| Pilot overview | `DESIGN_PARTNER_PILOT_OVERVIEW.md` | Sufficient | Explains the pilot clearly and stays aligned to repo reality. |
| Pilot scope and boundaries | `PILOT_SCOPE_AND_BOUNDARIES.md` | Sufficient | Keeps the wedge narrow and prevents scope drift. |
| Pilot limitations | `PILOT_LIMITATIONS.md` | Sufficient | States what the pilot does not claim. |
| Readiness truth | `CONTROL_PLANE_RELEASE_READINESS.md` | Sufficient | Gives honest readiness framing for diligence. |
| Blockers truth | `BLOCKERS.md` | Sufficient | States what still blocks production without undermining pilot honesty. |
| Buyer-ready offer summary | `PILOT_OFFER_ONE_PAGER.md` | Partial | Useful for a live conversation, but still depends on surrounding context. |
| Buyer FAQ | `PILOT_BUYER_FAQ.md` | Sufficient | Handles common early buyer questions clearly. |

## Must-Have Assets For Pilot Qualification And Discovery

| Asset | Current Source | Status | Why This Status |
| --- | --- | --- | --- |
| Design-partner conversation flow | `DESIGN_PARTNER_CONVERSATION_FLOW.md` | Sufficient | Defines the actual sequence for early conversations. |
| Pilot success metrics | `PILOT_SUCCESS_METRICS.md` | Sufficient | Makes pilot value measurable without overclaiming results. |
| Trust boundary summary | `PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md` | Sufficient | Helps handle early diligence and simulation boundaries. |
| Repo boundary summary | `REPO_BOUNDARY.md` | Sufficient | Keeps the control-plane versus verifier split clear. |
| Qualification rubric | Not yet written | Missing | Needed to say who is and is not a good design partner. |
| ICP definition | Not yet written | Missing | Needed for more efficient prospect targeting. |
| Buyer persona framing | Not yet written | Missing | Needed to tailor messaging for finance and technical stakeholders. |

## Must-Have Assets For Pilot Proposal And Closing

| Asset | Current Source | Status | Why This Status |
| --- | --- | --- | --- |
| Commercial proposal template | `PILOT_COMMERCIAL_PROPOSAL_TEMPLATE.md` | Sufficient | Usable once a design partner is qualified. |
| Statement of work template | `PILOT_STATEMENT_OF_WORK_TEMPLATE.md` | Sufficient | Gives a usable structure for scoped pilot delivery. |
| Scope and pricing framework | `PILOT_SCOPE_AND_PRICING.md` | Partial | Useful and honest, but still a framework rather than a standardized approved package. |
| Pilot delivery plan | `PILOT_DELIVERY_PLAN.md` | Sufficient | Helps define execution shape and sign-off path. |
| Pilot environment and trust inputs | `PILOT_ENVIRONMENT_REQUIREMENTS.md`, `PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md` | Sufficient | Strong enough for technical diligence in a controlled pilot. |
| Mutual success plan | Not yet written | Missing | Needed for a repeatable pilot-closing motion. |

## Useful Assets That Exist But Are Not First-Touch Essentials

| Asset | Current Source | Status | Why This Status |
| --- | --- | --- | --- |
| Pilot operator journey | `PILOT_OPERATOR_JOURNEY.md` | Sufficient | Useful once the buyer wants to understand operating flow. |
| Pilot architecture | `PILOT_ARCHITECTURE.md` | Partial | Strong for technical buyers, but not the right first document for most buyers. |
| GTM assumptions | `GTM_WORKING_ASSUMPTIONS.md` | Sufficient | Good internal guardrail, not a customer-facing asset. |
| Wedge justification | `PILOT_WEDGE_JUSTIFICATION.md` | Sufficient | Strong internal positioning support. |
| Commercial surface audit | `COMMERCIAL_SURFACE_AUDIT.md` | Sufficient | Good internal planning artifact, not buyer-facing. |
| GTM gap analysis | `PILOT_GTM_GAP_ANALYSIS.md` | Sufficient | Good internal planning artifact, not buyer-facing. |

## Assets That Are Still Missing But Should Wait Until After Early Conversations

These are useful, but they are not the next must-have assets for the current maturity stage:

- open-kernel versus paid-control-plane comparison matrix
- ROI framing document without invented outcomes
- final pilot readout template
- post-pilot conversion memo
- broader outreach messaging variants

These should follow only after the first round of design-partner conversations confirms the right buyer profile and objections.

## Minimum GTM Stack For The Next Pass

The minimum practical GTM stack for the next pass is:

1. `BUYER_PROBLEM.md`
2. `WEDGE_NARRATIVE.md`
3. `DESIGN_PARTNER_VALUE_HYPOTHESIS.md`
4. `PILOT_EXECUTIVE_BRIEF.md`
5. `DESIGN_PARTNER_PILOT_OVERVIEW.md`
6. `PILOT_SCOPE_AND_BOUNDARIES.md`
7. `PILOT_LIMITATIONS.md`
8. `PILOT_SUCCESS_METRICS.md`
9. `PILOT_OFFER_ONE_PAGER.md`
10. `PILOT_BUYER_FAQ.md`
11. `PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md`
12. `CONTROL_PLANE_RELEASE_READINESS.md`
13. `BLOCKERS.md`

## Summary

The repo already has enough material to support serious but still hands-on design-partner outreach.

What is still missing is not a broad collateral suite. What is still missing is a small set of repeatable GTM operating assets:

- qualification
- buyer tailoring
- pilot-closing discipline

That is the correct next layer for the current maturity stage.
