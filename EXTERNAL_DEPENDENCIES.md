# External Dependencies

## Purpose

This document lists the external systems and interfaces that Actenon Cloud depends on.

It is intended to prevent confusion about which capabilities are implemented in this repo and which are consumed from outside it.

## Core External Dependencies

### Separate Open Kernel Repo

Used for:

- canonical Action Intent contract family
- canonical receipt contract family
- execution-side semantics
- low-level execution or adapter contracts published by the kernel

Current repo reality:

- this repo aligns to pinned kernel contract copies for local development and testing
- this repo does not replace the open kernel
- a public read-only trace viewer, if shipped, belongs with that OSS surface rather than this repo

### Separate External Verifier Repo Or Interface

Used for:

- proof verification logic
- proof validation semantics
- any verifier outputs or interfaces used to assess issued proofs

Current repo reality:

- this repo issues proofs and stores proof records
- this repo does not embed or replace verifier logic
- proof verification remains an external dependency or integration concern

### Customer Execution Environment

Used for:

- ERP or accounts-payable proposal source
- downstream payment execution process
- receipt-producing execution path

Current repo reality:

- this repo does not claim to execute invoice payments itself
- this repo depends on customer or adjacent systems for actual payment operations and final settlement-side outcomes

## Infrastructure Dependencies

The pilot and service runtime also depend on:

- PostgreSQL
- object storage for evidence payloads
- ingress and TLS termination
- log shipping and operational monitoring systems

## Dependency Boundary Rule

If the capability is execution semantics, verifier logic, or settlement truth, it is an external dependency.

If the capability is governance, approval, proof issuance orchestration, release-state control, receipt indexing, or audit traceability, it belongs in Actenon Cloud.
