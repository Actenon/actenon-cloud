# GTM Working Assumptions

## Purpose

This document captures the working assumptions that should guide the next GTM passes for Actenon Cloud.

These are assumptions, not validated market facts. If design-partner evidence contradicts them, the materials should be updated.

## Product Assumptions

- The product being sold in the near term is the private commercial control plane, not the separate open kernel and not the separate verifier.
- The current commercially credible story is governance and traceability for invoice payment execution, not generalized finance automation.
- The repo's strongest claim is safe decision support and traceability around execution, not finished production execution infrastructure.

## Boundary Assumptions

- Canonical execution semantics come from the separate open kernel.
- Proof verification is provided by a separate verifier repo or verifier interface outside this repository.
- Actenon Cloud consumes, depends on, or integrates with those external interfaces rather than reimplementing them here.

## Buyer Assumptions

Primary buyer assumption:

- the likely economic buyer is a finance leader, controller, or finance operations leader who cares about payment risk, review ambiguity, and auditability

Technical buyer assumption:

- the likely technical buyer is an engineering, platform, security, or integration owner who can support pilot environment setup and system mapping

Pilot champion assumption:

- the most likely internal champion is a finance operations owner with recurring invoice payment review pain

Daily user assumption:

- the most likely pilot users are payment requesters, approvers, release managers, finance reviewers, and a small number of technical operators

## Problem Assumptions

- The fastest path to buyer interest is not abstract control-plane language; it is the concrete problem of unsafe or ambiguous outbound invoice payments.
- The most commercially legible near-term value is:
  - blocking invalid or unsafe payment proposals
  - making approvals and evidence explicit
  - making the release decision visible
  - connecting resulting receipts back to the original governed decision

## Pilot Motion Assumptions

- A serious design-partner pilot should stay limited to one tenant and one invoice-payment workflow family.
- A controlled pilot should stay time-boxed rather than open-ended.
- A pilot should be sold as a supervised governance pilot, not as a finished deployment.
- The customer must be willing to operate within explicit simulation boundaries for auth, signing, capability release, and observability.

## Messaging Assumptions

- Finance buyers will understand `payment proposal`, `approval`, `evidence`, `release decision`, and `receipt trace` faster than raw system nouns.
- Technical buyers still need the precise system boundary language behind those simpler terms.
- GTM materials should lead with the invoice payment control problem and introduce kernel or verifier details only after the commercial value is clear.

## Commercial Assumptions

- The next GTM passes should improve proposal quality, qualification, and conversion readiness before trying to broaden market scope.
- The working commercial model is hybrid across two phases: a fixed pilot or setup fee now, and later live pricing tied to proved and allowed consequential actions if the pilot proves value.
- Blocked, denied, or prevented actions should not be billed as usage because that would create a weaker trust model.
- Exact numeric pricing should remain controlled and proposal-based until there is real pilot evidence and a clearer qualification model.
- The open kernel alone is not the commercial product being sold; the commercial offer is the hosted control-plane layer above it.

## Evidence And Risk Assumptions

- No GTM material should claim numeric ROI, reference customers, or validated outcomes that do not yet exist.
- Early commercial materials should emphasize decision clarity, prevented unsafe payments, audit visibility, and reduction of manual ambiguity.
- The repo's honesty about what is simulated is a commercial strength and should be preserved.

## Asset Assumptions For Next GTM Passes

The next GTM materials should assume that the following already exist:

- pilot overview and scope
- pilot architecture and operator journey
- pilot success metrics, risks, and delivery plan
- pilot offer one-pager
- proposal and statement-of-work templates
- buyer FAQ
- pilot trust-boundary summary
- repo-level readiness and blocker documents

The next GTM materials should assume that the following still need work:

- ideal customer profile
- buyer personas
- qualification checklist
- outreach messaging
- open-kernel versus paid-control-plane comparison
- mutual success plan
- final pilot readout template

## Working Conclusion

Until validated otherwise, GTM work should position Actenon Cloud as a commercially serious but still early control plane for governed invoice payment execution, built above a separate open kernel and separate verifier interface, with a controlled pilot as the correct near-term motion.
