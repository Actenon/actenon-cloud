# Pilot Delivery Plan

## Purpose

This document defines how to deliver the invoice payment execution pilot without widening scope.

## Delivery Sequence

### Phase 0: Qualification And Scope Lock

Confirm:

- invoice payment execution is the agreed pilot wedge
- refunds and other finance workflows are out of scope
- the partner accepts the current simulation boundaries

### Phase 1: Environment And Access Setup

Complete:

- pilot environment creation
- non-default secret configuration
- tenant creation
- operator and service-principal setup
- signing key reference creation

### Phase 2: Policy And Data Mapping

Complete:

- invoice metadata mapping
- source and destination account reference mapping
- amount and threshold rules
- approval and evidence rules
- blocked destination and risk rules

### Phase 3: Shadow Validation

Run pilot examples without relying on actual automated execution:

- valid invoice payment
- denied invoice payment
- approval-required invoice payment
- evidence-required invoice payment
- structurally non-executable invoice payment

### Phase 4: Controlled Execution Pilot

Run a small, named set of invoice payments through:

- intake
- approval and evidence collection
- proof issuance
- capability release decision
- downstream customer execution process
- receipt ingestion
- audit trace review

### Phase 5: Exit Review

Review:

- safety wins
- operator usability
- receipt usefulness
- remaining production blockers
- whether to fund production-hardening work

## Technical Onboarding Steps

1. Stand up the pilot environment.
2. Configure tenant, policies, approvers, and release managers.
3. Create signing key references.
4. Map invoice payment proposal fields to the Action Intent envelope.
5. Agree receipt source and receipt posting path.
6. Run seeded validation scenarios.

## Validation Steps

The pilot should validate:

- intake contract validation
- deterministic policy behavior
- approval and evidence binding
- proof issuance preconditions
- escrow release and exception states
- receipt linkage and reconciliation
- audit trace usefulness

## Sign-Off Criteria

- the agreed seeded scenarios all complete successfully
- the partner confirms the pilot solved a real invoice-payment-control problem
- the partner accepts the documented limitations
- the partner can name the next production-hardening steps required

## What Must Be True To Move To Production Hardening

- the partner wants deeper execution integration
- the partner wants stronger identity and trust boundaries
- the partner wants managed signing
- the partner wants real capability release
- the partner wants broader operational assurances than the pilot provides
