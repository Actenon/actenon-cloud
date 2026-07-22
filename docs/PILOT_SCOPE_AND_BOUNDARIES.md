# Pilot Scope And Boundaries

## Chosen Pilot Use Case

The pilot use case is outbound invoice payment execution.

## Exact Action Types In Scope

In-scope kernel action profile:

- `action_type = "payment"`
- one invoice payment per Action Intent
- positive payment amount only
- one source account and one destination account per Action Intent
- one currency per Action Intent
- optional scheduled execution date through `requested_execution_date`

Recommended control-plane conventions for the pilot:

- `workflow_key = "payments.standard"`
- `external_reference = customer invoice identifier or ERP payment proposal identifier`
- `kernel_action_intent.metadata.invoice_id`
- `kernel_action_intent.metadata.invoice_number`
- `kernel_action_intent.metadata.vendor_id`
- `kernel_action_intent.metadata.erp_reference`

These metadata keys are pilot conventions, not kernel-owned canonical fields.

## Exact Actions Out Of Scope

Out of scope for this pilot:

- refunds
- chargebacks
- card capture flows
- payouts
- collections
- settlement instructions
- batch payments
- multi-invoice netting
- payroll
- vendor onboarding
- FX-specific workflow logic
- autonomous execution without human oversight
- production-grade connector or broker operations

## Why Refund Execution Was Not Chosen

Refund execution is not the recommended wedge because the current pinned kernel finance contract does not expose refund as a first-class `action_type`. Invoice payment execution is the more honest and stronger fit for current implementation reality.

## Control-Plane Boundary

Actenon Cloud owns:

- tenant-scoped intake
- policy evaluation
- approval workflow
- evidence linkage
- proof issuance orchestration and proof records
- capability escrow state
- receipt ingestion, indexing, reconciliation, and audit traces

Actenon Cloud does not own:

- kernel execution semantics
- verifier logic or proof validation decisions
- provider execution guarantees
- banking or payment-network side settlement truth

When proof verification is required, the control plane depends on a separate verifier repo or verifier interface outside this repository.

## Pilot Boundary On Automation

The pilot is a governed execution-decision workflow, not a claim of production payment automation.

The strongest honest pilot posture is:

- pre-execution governance is real
- receipt and traceability are real
- release state is real
- the actual capability handoff remains simulated unless a separate shallow integration is added
