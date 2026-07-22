# Exception Handling Runbook

## Purpose

This runbook defines how the managed invoice payment pilot should handle workflow exceptions during normal live operation.

It is about invoice payment cases that are held, blocked, failed, or routed to manual follow-up. It is not the same thing as a service outage runbook.

## Exception Classes

The pilot should treat these as the main exception types:

- held for approval
- held for evidence
- blocked by policy
- structurally non-executable
- approval expired or rejected
- proof issuance failed or rejected
- receipt mismatch or reconciliation requires manual review
- escrow revoked or quarantined

## First Response Principle

Start with the smallest responsible owner:

- customer workflow owners respond first to business-workflow exceptions
- provider operators respond first to runtime, deployment, or infrastructure failures

If there is any doubt, the customer finance operations owner and provider operations contact should review the case together.

## Exception Flow By Type

### Held For Approval

What the customer sees:

- the action appears in the held or exceptions queue
- approval state is pending

First responder:

- customer approver or customer finance reviewer

Resolution owner:

- customer approver for the approval decision
- customer tenant administrator if the wrong approver access or workflow setup is blocking progress

Provider involvement:

- only if approval assignment or permission behavior looks incorrect

Exit conditions:

- approval satisfied
- approval rejected
- action moved to manual follow-up because the approval cannot be resolved in normal pilot flow

### Held For Evidence

What the customer sees:

- the action appears as waiting on evidence
- evidence state is pending or incomplete

First responder:

- customer evidence contributor or customer finance reviewer

Resolution owner:

- customer team for supplying the missing artifact or external reference

Provider involvement:

- if upload, registration, or evidence binding behavior appears broken

Exit conditions:

- evidence submitted and linked
- action remains held pending additional requirements
- action is moved to manual follow-up

### Blocked By Policy

What the customer sees:

- decision outcome is denied
- the action is visible but not reviewable for override in product

First responder:

- customer finance reviewer

Resolution owner:

- customer policy owner for deciding whether the block is correct

Provider involvement:

- only if the customer believes the policy implementation or configuration is incorrect

Exit conditions:

- customer accepts the block as intended
- a policy change request is opened for future actions

The current pilot should not reopen or override this blocked action in product.

### Structurally Non-Executable

What the customer sees:

- the action failed structural validation or hard safety checks

First responder:

- customer requester or finance reviewer

Resolution owner:

- customer team for correcting the input or source data

Provider involvement:

- if the customer believes the intake contract handling is incorrect

Exit conditions:

- a corrected action is resubmitted
- the original invalid action is closed as non-executable

### Approval Expired Or Rejected

What the customer sees:

- approval state is expired or rejected
- there may be no in-product reopen path

First responder:

- customer finance reviewer

Resolution owner:

- customer approver lead and customer tenant administrator

Provider involvement:

- if the team needs help understanding whether the state reflects intended workflow behavior

Exit conditions:

- action closed and not progressed
- a new action is submitted if the business still wants to proceed

### Proof Issuance Failed Or Rejected

What the customer sees:

- proof stage shows failed or rejected
- action may move into manual follow-up

First responder:

- provider operations contact with customer finance reviewer copied in

Resolution owner:

- shared, depending on cause

Typical ownership split:

- customer owns missing approval or evidence inputs
- provider owns runtime or service behavior defects

Exit conditions:

- underlying control precondition fixed and the action is retried through the supported path
- action closed without progressing

### Receipt Mismatch Or Reconciliation Requires Manual Review

What the customer sees:

- receipt exists but reconciliation status is not matched

First responder:

- customer finance reviewer

Resolution owner:

- customer finance operations owner for business interpretation
- provider support for trace, linkage, or ingestion troubleshooting

Exit conditions:

- customer accepts the receipt outcome with notes outside the product
- a corrected receipt is ingested if appropriate
- the case is documented as a pilot exception

### Escrow Revoked Or Quarantined

What the customer sees:

- escrow or execution state shows revoked or quarantined

First responder:

- provider operations contact and customer finance reviewer together

Resolution owner:

- shared, because these are high-sensitivity control states

Exit conditions:

- the action is closed as intentionally halted
- the issue is escalated into incident handling if the state suggests product or runtime failure

## Manual Escalation Path

If an exception cannot be resolved by the normal workflow owner:

1. capture the `action_intent_record_id`
2. capture the time window and any `X-Request-ID`
3. review the action trace
4. classify the issue as:
   - customer business decision
   - customer configuration issue
   - provider runtime or workflow issue
   - external dependency issue
5. route it through the named customer and provider contacts

## What The Customer Should Expect

During the pilot:

- blocked actions stay blocked
- some held cases can be resolved directly in product
- some failed or exceptional cases still require manual coordination outside the product

That is a real pilot boundary, not a hidden limitation.
