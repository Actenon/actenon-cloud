# Commercial Baseline

## Purpose

This document defines the current commercial baseline for Actenon Cloud before broader GTM materials are written.

It is specific to the chosen invoice payment execution pilot wedge. It does not redesign the product, widen scope, or treat the current repo as production-ready.

## Current Product Truth

Actenon Cloud is the private commercial control-plane service that sits above a separate open kernel and a separate external proof verifier interface. This repository is not the open kernel and is not the verifier.

What exists in this repo today:

- tenant-scoped Action Intent intake for finance payment actions
- deterministic policy evaluation
- approval and evidence workflows
- bounded proof issuance and development-grade signing
- capability escrow lifecycle tracking
- receipt ingestion, reconciliation, and audit query surfaces
- basic multi-tenant admin and early auth foundations

Current readiness posture:

- internal development readiness: Green
- design-partner pilot readiness: Amber
- production deployment readiness: Red

## Current Commercial Truth

The strongest honest commercial story is narrow:

Actenon Cloud can serve as a governed control and traceability layer for outbound invoice payment execution in a controlled pilot.

That commercial story is credible because the implemented system can already support:

- payment proposal intake
- rule-based allow or deny decisions
- approval and evidence requirements
- bounded proof issuance for the exact payment payload
- tightly scoped release-state tracking
- receipt linkage and searchable audit traces

That commercial story must stay bounded because the repo does not yet claim:

- production-grade payment execution
- production-grade provider integration
- enterprise-ready identity
- managed signing maturity
- real protected-resource release enforcement

Current pricing and packaging truth:

- the pilot is sold first as a fixed pilot or setup fee covering workflow mapping, configuration, validation, and supervised delivery
- if the pilot proves value and the partner wants to continue, the working live commercial direction is usage pricing tied to proved and allowed consequential actions
- blocked, denied, or prevented actions should not be billed as usage because that weakens trust and muddies incentive alignment

## What Is Already Commercially Strong

### 1. The wedge is narrow and believable

Outbound invoice payment execution is a legible finance control problem. It is easier for a design partner to evaluate than a broad platform story.

### 2. The implementation supports the story

The repo already contains real APIs and tested workflow slices for the governance path around invoice payment execution. The commercial story is not disconnected from implementation reality.

### 3. The open-versus-paid boundary is clear

The repo distinguishes:

- separate open kernel and external verifier responsibilities
- paid control-plane responsibilities above those interfaces

That makes the commercial layer easier to explain without pretending this repo contains everything.

### 4. The pilot package is real

The repo already includes:

- pilot overview, scope, architecture, operator journey, success metrics, delivery plan, risk register, limitations, and executive brief
- one-pager, proposal template, statement-of-work template, buyer FAQ, pricing framework, and pilot trust summary

### 5. The repo is honest

The current materials consistently state what is simulated, what is early, and what still blocks production. That is commercially useful in serious design-partner conversations.

## What Is Still Too Technical

The commercial surface is still stronger with technical buyers than with finance buyers.

Common friction points:

- core repo documents still lead with system structure before buyer pain
- system-native terms appear early: `Action Intent`, `proof issuance`, `capability escrow`
- some materials assume comfort with kernel and verifier boundaries before buyer value is established

## What Is Already Written Versus Still Missing

### Already Written

- a credible invoice-payment pilot narrative
- pilot scope and boundaries
- pilot architecture and operator flow
- pilot success metrics, risks, delivery plan, and limitations
- commercial offer one-pager and proposal scaffolding
- statement-of-work template
- buyer FAQ
- pilot security and trust-boundary summary
- repo-level readiness and blocker documents

### Still Missing For Broader GTM Work

- ideal customer profile
- buyer persona framing
- qualification rubric for design partners
- outreach-ready messaging for finance and technical buyers
- open-kernel versus paid-control-plane packaging matrix
- ROI narrative that does not invent outcomes
- mutual success plan and final pilot readout assets
- clearer conversion story from pilot success to paid production-hardening work

## Commercial Guardrails For Next Passes

The next GTM passes should preserve the following guardrails:

- keep invoice payment execution as the first and only pilot wedge
- describe proof verification as external to this repo
- keep the open kernel and verifier as separate dependencies or interfaces
- do not imply that simulated capability release is production execution
- do not claim production readiness
- keep the pricing story tied to a fixed pilot or setup fee plus later usage on proved and allowed actions
- do not charge blocked actions as usage in the pilot-stage commercial model
- translate technical terms into buyer language where possible without changing system truth

## Baseline Conclusion

The commercial baseline is stronger than a pure engineering repo and strong enough to support serious pilot packaging.

It is not yet a complete GTM surface. The next work should focus on buyer qualification, buyer-language positioning, open-to-paid conversion framing, and repeatable pilot-selling assets without changing the underlying product story.
