# Mutual Success Plan Template

## Purpose

This template is for a design-partner pilot of Actenon Cloud focused on outbound invoice payment execution.

It is meant to be used in real customer conversations. It should make the pilot scope, success measures, operating cadence, and current limitations explicit before the pilot starts.

This template does not replace the statement of work. It is the practical success plan that both teams can review together.

## 1. Pilot Summary

- Customer: `[customer name]`
- Provider: `Actenon Cloud`
- Pilot name: `[pilot name]`
- Workflow in scope: `[one outbound invoice payment workflow]`
- Pilot start date: `[date]`
- Pilot end date: `[date]`
- Planned duration: `[typically 6-8 weeks]`
- Customer sponsor: `[name]`
- Customer operations owner: `[name]`
- Customer technical owner: `[name]`
- Actenon pilot owner: `[name]`

## 2. Workflow In Scope

The pilot workflow covered by this plan is:

- one outbound invoice payment workflow
- one managed tenant
- one controlled pilot environment

Example scope statement:

`Actenon Cloud will govern one outbound invoice payment workflow from intake through policy decision, approval or evidence handling when required, proof packaging, release-state tracking, receipt linkage, and trace review.`

The following should be filled in explicitly:

- source system for payment proposals: `[ERP, AP system, internal service, other]`
- downstream execution process: `[manual ops, treasury ops, payment platform, other]`
- receipt or execution confirmation source: `[system or process]`
- expected operator roles: `[requester, approver, reviewer, finance ops, other]`
- in-scope currencies or payment types: `[list]`
- expected average weekly volume: `[count]`

## 3. What Success Would Mean

The pilot is successful if both teams can say all of the following are true:

- the in-scope invoice payment workflow was governed end to end inside the agreed boundary
- operators could tell which actions were allowed, held for review, or refused
- approvals and evidence requirements were understandable and operable
- linked trace output was useful in explaining what happened to a payment
- the customer can judge whether the workflow is worth production-hardening next

The pilot is not required to prove:

- broad workflow coverage
- self-serve SaaS readiness
- production-grade auth, signing, or hosting maturity
- verifier functionality inside this repo
- direct payment-network execution by this product

## 4. Metrics To Be Measured

The pilot should track a small set of operating metrics every week.

### Volume And Outcome Metrics

- total in-scope invoice payment actions submitted
- count of actions allowed
- count of actions held for approval
- count of actions held for evidence
- count of actions refused or blocked by policy
- count of actions marked structurally non-executable

### Review And Resolution Metrics

- count of held actions reviewed within agreed operating window
- time from intake to initial safe decision
- time from approval request creation to approval satisfaction
- time from evidence request to evidence completion when evidence is required
- count of actions requiring manual follow-up outside the product

### Trace And Completion Metrics

- percentage of actions with complete approval visibility when approval is required
- percentage of actions with complete evidence linkage when evidence is required
- percentage of actions with linked receipts
- percentage of actions with a usable end-to-end trace across action, approval, evidence, proof, and receipt state

### Trust And Usability Metrics

- number of cases where operators said the system made the payment decision easier to explain
- number of cases where the system surfaced a meaningful block, hold, or exception before execution
- sponsor and operator confidence level at midpoint and final review: `[low / medium / high]`

## 5. Target Success Thresholds

Fill these in before kickoff.

- minimum actions to evaluate during pilot: `[count]`
- minimum allowed actions traced end to end: `[count]`
- minimum blocked or refused actions observed: `[count]`
- minimum held and reviewed actions observed: `[count]`
- minimum receipt-linked actions observed: `[count]`
- target percentage of required approvals visible in one trace: `[percentage]`
- target percentage of required evidence visible in one trace: `[percentage]`
- maximum tolerated unresolved manual follow-up backlog at pilot end: `[count]`

Suggested minimum validation events:

- at least one allowed invoice payment traced end to end
- at least one blocked or refused invoice payment
- at least one held action that required approval or evidence review
- at least one receipt-linked action with trace review

## 6. Pilot Duration And Phases

Suggested structure:

### Phase 1. Setup

- duration: `[1-2 weeks]`
- confirm workflow, actors, policies, evidence expectations, and operating contacts
- configure environment and pilot access
- validate intake and receipt inputs

### Phase 2. Controlled Run

- duration: `[3-4 weeks]`
- run the in-scope workflow with real or pilot-designated payment actions
- review held, allowed, and refused cases weekly
- track metrics and operating exceptions

### Phase 3. Exit Review

- duration: `[1 week]`
- review metrics, operator feedback, limitations, and next-step recommendation
- decide whether to stop, extend narrowly, or move into production-hardening work

## 7. Review And Reporting Cadence

The pilot should run with a simple, explicit cadence.

### Weekly Operating Review

- audience: customer operations owner, customer technical owner, Actenon pilot owner
- focus:
  - action counts
  - allowed / held / refused outcomes
  - held queue status
  - incidents or manual follow-up items

### Weekly Metrics Review

- audience: customer operations owner, approver lead when relevant, Actenon pilot owner
- focus:
  - blocked / allowed / reviewed action metrics
  - approval turnaround
  - evidence completion
  - receipt linkage
  - trace usefulness

### Biweekly Sponsor Review

- audience: customer sponsor, customer operations owner, customer technical owner, Actenon lead
- focus:
  - whether the pilot is producing confidence
  - whether the pilot remains inside scope
  - whether the next step is becoming clearer

### Incident Communication

Do not wait for weekly review if there is:

- runtime unavailability
- repeated workflow failure
- materially confusing trace behavior
- receipt mismatch with operational significance
- a pilot pause decision

## 8. Customer Responsibilities

The customer is expected to provide:

- named sponsor, operations owner, and technical owner
- one clearly defined invoice payment workflow
- sample or real pilot payment actions inside the agreed scope
- approval policy inputs and evidence expectations
- receipt or execution confirmation inputs
- timely participation in weekly reviews

## 9. Actenon Responsibilities

Actenon is expected to provide:

- managed pilot delivery
- environment and workflow setup support
- operator guidance during the pilot
- weekly reporting support
- clear disclosure of current product limitations
- final pilot findings and next-step recommendation

## 10. Exit Conditions

At the end of the pilot, the teams should explicitly choose one of the following outcomes:

- `Proceed to hardening`: the workflow value is real and the next step is targeted production-hardening work
- `Extend narrowly`: the pilot showed promise but needs one additional short, scoped iteration
- `Stop`: the workflow, customer readiness, or product maturity is not a fit right now

The final review should record:

- what worked
- what did not work
- whether operators trusted the outcome visibility
- whether the trace was useful
- what remained manual or early
- what hardening work would be required next

## 11. Explicit Limitation Disclosures

These disclosures should be reviewed with the customer before kickoff and repeated in the final review.

Current pilot limitations:

- the pilot covers one outbound invoice payment workflow, not a broad finance platform
- hosting is managed and single-tenant, not self-serve SaaS
- auth is still early and may require provider-assisted setup
- signing is still early and not yet a managed KMS or HSM path by default
- evidence uploads are currently filesystem-backed
- proof verification remains outside this repo through a separate verifier boundary
- capability release and execution-side enforcement remain limited relative to a finished production deployment
- observability is pilot-grade, not a full enterprise monitoring stack

The customer should explicitly acknowledge that the pilot is for design-partner validation, not a production-readiness claim.

## 12. Decision Record

Complete this section at kickoff and again at exit.

- success definition agreed: `[yes/no]`
- workflow scope agreed: `[yes/no]`
- customer owners named: `[yes/no]`
- limitations reviewed: `[yes/no]`
- target metrics agreed: `[yes/no]`
- exit path to evaluate: `[stop / extend narrowly / proceed to hardening]`

## 13. Simple Conversation Summary

If the customer asks for the short version, use this:

`This pilot is one managed invoice payment workflow. We will measure how many actions were allowed, held, reviewed, and refused; whether approvals, evidence, and receipts were visible in one trace; whether operators trusted the workflow more; and whether the result justifies production-hardening work next.`
