# ICP Qualification Rubric

## Purpose

This rubric helps the team decide whether a prospect is a strong design-partner fit for the Actenon Cloud invoice payment pilot.

It is intentionally narrow. It is not a general ideal-customer-profile document for a broad SaaS motion. It is a qualification filter for one managed pilot:

- one design partner
- one managed tenant
- one outbound invoice payment workflow

## What This Rubric Is Optimizing For

A strong design partner for this pilot should have:

- real consequential invoice payment volume
- meaningful audit, compliance, or control pressure
- enough workflow maturity to isolate one payment path
- enough technical receptiveness to work through a supervised pilot

The goal is not to find the biggest logo. The goal is to find a partner where the pilot can produce a credible operating result in a narrow scope.

## Scoring Model

Score each category from `0` to `3`.

- `0` = poor fit
- `1` = weak fit
- `2` = plausible fit
- `3` = strong fit

Then apply the decision thresholds at the end.

## Qualification Categories

### 1. Consequential Action Volume

This pilot is strongest when the prospect has enough invoice payment activity for control decisions to matter operationally.

- `3`: More than `1,000` outbound invoice payments per month, or lower volume but very high average payment value and repeated approval friction.
- `2`: Roughly `200` to `1,000` outbound invoice payments per month, with recurring review, approval, or evidence bottlenecks.
- `1`: Fewer than `200` payments per month and only occasional control pain.
- `0`: Very low volume, irregular payments, or no meaningful invoice payment review burden.

Questions to ask:

- How many outbound invoice payments do you process per month?
- How many of those require review, approval, exception handling, or evidence collection?
- What percentage are financially consequential enough that an incorrect payment is painful?

### 2. Audit And Compliance Need

This pilot is a better fit when the prospect has a real need to explain why a payment was allowed, held, or refused.

- `3`: Clear internal-control, audit, compliance, SOX-like, delegated-authority, or board-level pressure around payment approvals and traceability.
- `2`: Recurring internal audit, controller, finance-ops, or procurement pressure, but not yet a major compliance program.
- `1`: Mostly convenience-driven workflow pain with limited audit consequences.
- `0`: No serious need for decision traceability, evidence linkage, or approval accountability.

Questions to ask:

- What happens today when someone asks why a payment was approved?
- Is there a real audit, controller, or finance-risk review process behind this?
- Do you need linked approvals, evidence, and receipts in one trace?

### 3. Agent/Workflow Maturity

The design partner does not need a perfect automation stack, but they do need a stable enough workflow to isolate one governed payment path.

- `3`: The team can clearly define one invoice payment workflow, actors, approval rules, evidence requirements, and exception states. They already operate structured finance workflows or agent-assisted processes.
- `2`: The workflow exists and is repeated, but some decision points or evidence expectations still need light cleanup during pilot setup.
- `1`: The process is inconsistent, highly person-dependent, or changes every week.
- `0`: No stable invoice payment workflow exists, or the prospect wants Actenon Cloud to invent the process for them.

Questions to ask:

- Can you isolate one invoice payment workflow for the pilot?
- Who submits, reviews, approves, and executes it today?
- What evidence or supporting context is expected before release?
- Are there existing agent, automation, AP, ERP, or approval systems involved?

### 4. Technical Receptiveness

The current product is a managed pilot with real APIs, real traces, and honest technical limitations. The partner needs to be comfortable working that way.

- `3`: The prospect has an engaged technical owner, is comfortable with API-led integration, can support receipt or event inputs, and accepts a managed pilot with explicit early-stage boundaries.
- `2`: The prospect has workable technical support but limited bandwidth; integration is possible if kept narrow and supervised.
- `1`: Technical ownership is weak, integration expectations are fuzzy, or the team expects a turnkey product with no implementation involvement.
- `0`: The prospect rejects pilot constraints, wants polished self-serve SaaS behavior, or cannot support even minimal integration work.

Questions to ask:

- Who will own technical setup and environment access?
- Can your team support a narrow API and receipt-integration path?
- Are you comfortable with a managed pilot rather than self-serve onboarding?

### 5. Scope Discipline

The best pilot partner accepts the invoice payment wedge as the first step.

- `3`: The prospect accepts one outbound invoice payment workflow as a meaningful first deployment and does not need refunds, batch payouts, treasury orchestration, or broad workflow expansion in phase one.
- `2`: The prospect wants future expansion but accepts the initial wedge cleanly.
- `1`: The prospect says yes to the wedge but repeatedly tries to pull the conversation toward broader finance platform scope.
- `0`: The prospect fundamentally wants a wider platform now.

Questions to ask:

- If we only govern one invoice payment workflow first, is that still valuable?
- What adjacent workflows are most likely to creep into scope?
- Can broader asks wait until after pilot proof?

### 6. Pilot Operating Capacity

This product is currently best suited to a design partner that can operate with a provider-supported pilot rhythm.

- `3`: The prospect has a finance sponsor, an operational owner, and a technical owner who can all support a supervised pilot over the evaluation period.
- `2`: The sponsor and technical owner are real, but day-to-day operator availability is still being organized.
- `1`: There is interest, but no clear operator owner or sponsor with authority.
- `0`: No credible internal owner exists for finance, operations, or technical setup.

Questions to ask:

- Who is the executive or finance sponsor?
- Who will operate the held or review queue?
- Who will work with us on setup, auth, evidence, and receipt inputs?

## Decision Thresholds

Use the rubric this way:

- `16-18`: Strong design-partner fit. Advance if there is no red-line disqualifier.
- `12-15`: Possible fit. Advance only with a very narrow pilot scope and explicit expectation-setting.
- `8-11`: Weak fit. Do not prioritize unless there is an unusually strong strategic reason.
- `0-7`: Poor fit. Do not pursue for this pilot.

## Red-Line Disqualifiers

Do not advance the prospect into serious pilot work if any of the following are true:

- They do not have a meaningful outbound invoice payment workflow.
- They want a broad finance platform rather than one governed invoice payment path.
- They cannot articulate a real control, audit, or approval problem.
- They expect finished production-grade auth, signing, hosting, or provider execution in the pilot.
- They cannot supply a technical owner.
- They cannot supply a finance or operations owner.
- They cannot support even a narrow managed integration and receipt input path.
- Their workflow is so unstable that one payment path cannot be isolated for `6-12` weeks.

## Strongest Fit Signals

These signals should materially increase confidence:

- Invoice payments are frequent enough that review friction is operationally painful.
- Incorrect or weakly-governed payments have clear financial, audit, or reputational cost.
- The prospect already has approval rules, evidence expectations, or delegated authority logic, even if execution is fragmented.
- A controller, finance systems lead, AP lead, or similar owner is actively trying to improve payment traceability.
- The technical team is willing to work through a managed pilot with real but narrow integration work.
- The prospect sees immediate value in `allow`, `hold`, and `refuse` decisions being visible and explainable before execution.

## Weak But Potentially Salvageable Cases

Some prospects are not immediate strong fits but can still be reconsidered later:

- They have real control pain, but volume is not yet high enough to justify near-term pilot effort.
- They want the wedge, but internal ownership is not ready yet.
- They have the right technical mindset, but the target workflow is still being standardized.
- They are strategically valuable, but the first workflow should be prepared internally before pilot start.

These should usually be deferred rather than forced into the current pilot motion.

## Recommended Qualification Workflow

1. Confirm the prospect has a real outbound invoice payment workflow.
2. Score all six categories during or immediately after the first serious meeting.
3. Check for any red-line disqualifier.
4. If the score is `16+`, move to pilot scoping.
5. If the score is `12-15`, require explicit scoping discipline and named owners before advancing.
6. If the score is below `12`, do not prioritize for the current design-partner wave.

## One-Line Summary Test

The best current design partner is a team with enough invoice payment volume and control pain to care, enough workflow maturity to isolate one path, and enough technical and operational ownership to run a managed pilot honestly.
