# Pilot Integration Checklist

## Purpose

This checklist captures what the design partner must provide to make the invoice payment execution pilot workable.

## Identity And Access Inputs

- one customer pilot sponsor
- one customer technical owner
- one finance operations lead
- at least one payment requester
- at least one approver
- at least one release manager
- optional service principal for API-driven payment proposal submission

## Policy Inputs

- payment amount thresholds
- blocked destinations or country rules
- approval thresholds
- evidence requirements for higher-risk payments
- requester separation-of-duties expectations
- distinct approver expectations

## Invoice Payment Data Inputs

- invoice identifier
- invoice number
- vendor or payee identifier
- ERP or payable-system reference
- amount
- currency
- source account reference
- destination account reference
- requested execution date when applicable

Recommended mapping:

- canonical payment fields in `kernel_action_intent`
- invoice and ERP references in `external_reference` and `kernel_action_intent.metadata`

## Approval And Evidence Inputs

- list of allowed approver principals for the pilot
- evidence types to require for higher-risk payments
- example evidence artifacts such as invoice PDF, approval memo, or vendor confirmation
- approval expiry expectations if used

## Protected Resource And Connector Inputs

Minimum pilot mode:

- customer agrees that capability release is simulated
- customer provides the downstream process that actually executes the payment
- customer provides or can derive `provider_execution_ref` for receipts

Optional deeper pilot mode:

- customer provides a shallow adapter endpoint or operator workflow that accepts a release token, performs payment execution, and returns a receipt payload

## Receipt Inputs

- `receipt_id`
- `intent_id`
- `occurred_at`
- `outcome`
- `action_intent_digest`
- `provider_execution_ref`
- optional `settlement_reference`

## Environment Inputs

- pilot environment URL and TLS ingress
- managed PostgreSQL
- object storage location
- non-default secrets
- log shipping destination

## Readiness Checklist

- tenant created
- policy created and activated
- operator users available
- service principal available if needed
- evidence examples loaded
- signing key reference created
- receipt source agreed
- pilot action naming and metadata conventions agreed
