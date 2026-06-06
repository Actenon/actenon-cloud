# Pilot Security And Trust Boundary Summary

## Purpose

This document gives a plain-language trust and security summary for the invoice payment execution governance pilot.

It is meant for early customer diligence and pilot review. It is not a claim of full production security maturity.

## What The Pilot Handles

The pilot handles governance-layer data around invoice payment execution, including:

- payment proposal payloads
- invoice and ERP reference metadata
- approval records
- evidence metadata and uploaded artifacts
- issued proof records
- escrow lifecycle records
- receipt records
- audit and reconciliation records

Typical customer systems and users involved:

- ERP or payable system that produces the invoice payment proposal
- finance operators who request, approve, and review payments
- a downstream payment process that actually executes the payment
- a receipt-producing system or kernel-connected execution path

## What The Pilot Does Not Handle

The pilot does not claim to be:

- the execution kernel
- the verifier
- the final source of payment settlement truth
- a finished production payment execution platform

It also does not claim:

- enterprise-ready identity
- managed signing maturity
- real provider-broker enforcement
- fully hardened production operations

## Trust Boundary

The current trust boundary is:

- the open kernel provides the public execution and contract layer
- Actenon Cloud provides the paid governance and traceability layer above it
- the customer or downstream execution process still performs the actual payment step in the current pilot model

## Current Security Reality

Implemented today:

- tenant-scoped data model
- policy and access-control foundations
- structured logs
- audit records
- receipt and reconciliation traceability

Still early today:

- operator auth
- service identity
- signing trust
- observability stack

## What Is Simulated

The most important simulated area is capability release.

The repo can represent and govern the release decision, but it does not yet provide a finished external protected-resource broker or provider execution enforcement path.

## Environment Expectations

The pilot should run in a controlled environment with:

- non-default secrets
- managed PostgreSQL
- mounted persistent evidence storage
- TLS ingress
- central log shipping

## Storage And Evidence

The pilot supports evidence metadata and uploaded artifacts.

The current implementation uses a filesystem-backed evidence adapter. A serious pilot should run with mounted persistent storage and must not treat ephemeral local container disk as an acceptable operating pattern.

## Signing

Proof issuance exists, but the default signing path is still early. The current repo does not claim managed KMS or HSM maturity in the pilot baseline.

## Honest Security Summary

The honest claim is:

this pilot is credible for controlled design-partner evaluation of invoice payment governance, but it is not yet a fully hardened production trust boundary.

If the pilot succeeds, the next step is a separate production-hardening path rather than direct production rollout.
