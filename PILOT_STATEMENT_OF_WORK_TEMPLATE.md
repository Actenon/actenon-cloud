# Pilot Statement Of Work Template

## Purpose

This template defines the statement of work for the invoice payment execution governance pilot.

## 1. Parties

- Customer: `[customer name]`
- Service provider: `Actenon Cloud`
- Effective date: `[date]`

## 2. Objective

The purpose of this statement of work is to run a controlled pilot for outbound invoice payment execution governance using Actenon Cloud.

## 3. Scope Of Work

Included work:

- tenant setup
- pilot-scope policy and workflow configuration
- invoice payment proposal intake setup
- approval and evidence workflow enablement
- proof issuance enablement
- capability escrow lifecycle enablement
- receipt ingestion and audit trace review
- seeded validation scenarios
- pilot review sessions
- final findings review and next-step recommendation

## 4. Explicit Exclusions

Excluded work:

- refunds
- generalized payment workflow expansion
- production SSO rollout
- managed KMS or HSM rollout
- production release-broker integration
- production observability and deployment hardening
- broad user-interface work

## 5. Customer Responsibilities

The customer will provide:

- named pilot stakeholders
- environment and security approvals
- invoice payment sample scenarios
- policy thresholds and rules
- approver and operator identities
- receipt source and operational process for executed payments

Customer systems typically involved:

- ERP or payable system
- downstream payment operations process
- receipt-producing execution system or kernel-connected receipt source

## 6. Actenon Cloud Responsibilities

Actenon Cloud will provide:

- pilot delivery ownership
- technical setup guidance
- policy and workflow enablement
- pilot support during the agreed period
- final pilot findings review

## 7. Deliverables

Expected deliverables:

- configured pilot tenant and workflow
- pilot policy configuration
- seeded validation results
- receipt and audit trace demonstration
- pilot findings summary
- recommendation on next-step production-hardening work
- signed-off record of what remained simulated during the pilot

## 8. Timeline

- suggested duration: `6 to 8 weeks`
- kickoff: `[date]`
- setup complete: `[date]`
- validation complete: `[date]`
- controlled pilot run complete: `[date]`
- final review complete: `[date]`

## 9. Acceptance Criteria

The pilot will be considered complete when:

- the agreed scenarios have been run
- the customer has reviewed the resulting trace outputs
- limitations and risks remain explicitly acknowledged
- a final go, no-go, or harden-next decision is recorded

## 10. Limitations

This statement of work does not imply:

- production readiness
- real payment execution by this repo
- real provider-broker enforcement
- final production trust posture
- expansion beyond the invoice payment execution wedge unless separately agreed
