# Pilot Operator Journey

## Roles

The recommended pilot roles are:

- payment requester
- approver
- release manager
- finance reviewer
- technical operator

## Step 1: Propose Invoice Payment

The payment requester submits an Action Intent through `POST /api/v1/action-intents`.

For the pilot:

- `action_type` should be `payment`
- the payload should include source account, destination account, amount, currency, and optional execution date
- the invoice identifier should be carried in `external_reference` and or metadata

## Step 2: Policy Evaluation

Actenon Cloud evaluates:

- hard rules
- tenant workflow policy
- dynamic evaluation context

Possible outcomes:

- `allow`
- `deny`
- `approval_required`
- `needs_evidence`
- `structurally_non_executable`

## Step 3: Approval And Evidence Collection

If the payment needs evidence:

- the operator uploads or registers evidence through `/api/v1/evidence`

If the payment needs approval:

- approval requests already exist from intake
- an approver reviews the payment and submits a decision through `/api/v1/approvals/{approval_request_id}/decisions`

## Step 4: Proof Issuance

Once controls are satisfied, an operator requests proof issuance through `/api/v1/issuance/proofs`.

The proof is bound to:

- exact Action Intent digest
- exact audience
- exact scope
- nonce
- expiry

## Step 5: Execution Allowed Or Refused

If proof issuance fails:

- execution should not proceed
- the operator reviews missing approvals, missing evidence, or policy denial

If proof issuance succeeds:

- the release manager creates an escrow hold
- the release manager releases the capability
- the downstream execution process either consumes it or the payment remains unexecuted

## Step 6: Receipt Review

After the customer payment process runs, a receipt is ingested through `/api/v1/receipts`.

Operators can then review:

- receipt outcome
- linked approvals
- linked evidence
- issued proof
- escrow record
- reconciliation summary
- audit events

The main query surface is `/api/v1/audit/traces/{action_intent_record_id}`.

## Exception Handling In The Pilot

Expected pilot exception paths:

- denied payment due to policy
- structurally non-executable payment due to malformed or unsafe request
- missing evidence
- missing or expired approval
- revoked or quarantined escrow path
- mismatched receipt binding that requires manual review

These exception paths are part of the pilot value, not just failure cases. They show whether the control plane makes invoice payment risk more understandable before execution.
