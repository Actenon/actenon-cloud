# Evidence Model

## Purpose

This document defines the first real evidence intake and storage model for Actenon Cloud.

Release 1 keeps the scope intentionally narrow: evidence is a control-plane artifact that can be registered, uploaded, linked to an Action Intent, linked to an approval request, and later cited by approval decisions or future proof issuance workflows.

## Boundary

Evidence objects are control-plane records.

The control plane does not redefine kernel evidence references or kernel receipt artifacts. It stores its own evidence metadata and uploaded files around the governed workflow that sits above the open kernel.

## Current Endpoints

- `GET /api/v1/evidence`
- `GET /api/v1/evidence/{evidence_object_id}`
- `GET /api/v1/evidence/{evidence_object_id}/content`
- `POST /api/v1/evidence/register`
- `POST /api/v1/evidence/upload`

## Current Model

Each `EvidenceObject` stores:

- tenant scope
- linked `action_intent_record_id`
- optional linked `approval_request_id`
- `evidence_type`
- `storage_mode`
- `storage_ref`
- optional filename and media type
- optional content digest and size
- uploader principal
- arbitrary evidence metadata
- optional expiry timestamp
- current evidence object status

## Storage Modes

The evidence record model supports four storage modes:

- `filesystem`
- `object_store`
- `external_uri`
- `inline_metadata_only`

The current `upload` endpoint still writes to a filesystem-backed storage adapter and returns `storage_mode = filesystem`.

That is the current implementation truth for this repo build. It should not be described as object-store-backed upload behavior.

The current `content` endpoint is intentionally narrow:

- it serves filesystem-backed uploaded evidence
- it can be extended to other storage backends through explicit adapters
- it does not proxy arbitrary external URIs
- metadata-only evidence remains metadata-only
- object-store content retrieval is not implemented in the current repo build

The current `register` endpoint is used for:

- filesystem or object-store references that were already created outside the upload path
- externally hosted evidence references
- metadata-only evidence registration
- previously stored artifacts that already have a stable custody reference

## Backend Selection

The runtime now has an explicit evidence upload backend selection seam.

Current configuration path:

- `ACTION_CONTROL_PLANE_EVIDENCE_UPLOAD_BACKEND=filesystem`
- `ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT=...`

Future object-store path:

- `ACTION_CONTROL_PLANE_EVIDENCE_UPLOAD_BACKEND=object_store`
- `ACTION_CONTROL_PLANE_EVIDENCE_OBJECT_STORE_BUCKET=...`
- `ACTION_CONTROL_PLANE_EVIDENCE_OBJECT_STORE_PREFIX=...`
- optional `ACTION_CONTROL_PLANE_EVIDENCE_OBJECT_STORE_ENDPOINT=...`

Current status of that future path:

- the object-store adapter interface is now explicit in code
- the current repo build does not implement live object-store upload or content retrieval
- selecting the object-store upload backend is a configuration and interface path, not a claim of production readiness
- the current runtime still expects `ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT` because filesystem remains the only working upload backend in this repo build

This keeps the control-plane evidence contract stable while making the storage upgrade path estimable.

## Action Intent Binding

Evidence binds to the control plane in two ways:

- directly to an `ActionIntentRecord`
- optionally to an `ApprovalRequest`

This keeps evidence reusable for:

- approval review
- future proof or PCCB issuance
- audit and export workflows

The Action Intent stores an aggregate `evidence_state`:

- `not_required`
- `pending`
- `satisfied`
- `expired`
- `canceled`

## Policy Binding

The policy engine now supports an optional `evidence_requirement` object on each rule. The current shape is:

- `minimum_count`
- `allowed_evidence_types`
- `expires_in_seconds`

If a rule returns `needs_evidence` without an explicit requirement object, the service creates a minimal default requirement of one evidence object of any type.

## Current Evidence Evaluation

For a required evidence set:

- active evidence objects are counted toward `minimum_count`
- `allowed_evidence_types` restrict which objects may satisfy the requirement
- expired evidence does not satisfy the requirement
- if required evidence is missing, the Action Intent remains `pending`
- if only expired evidence is present, the Action Intent moves to `expired`

## Upload And Integrity

The current upload path computes and stores:

- a content digest
- file size
- a stable backend-specific storage reference

For the currently implemented backend, that reference is a filesystem-relative path beneath the configured evidence storage root.

This is enough to support later custody and proof-binding work without pretending that full object-store lifecycle controls already exist.

## What Is In Scope Now

- metadata registration for evidence
- direct upload of evidence payloads
- link evidence to Action Intents
- link evidence to approval requests
- expiry handling for evidence objects
- aggregate Action Intent evidence state
- evidence citation from approval decisions

## What Is Deferred

- malware scanning and quarantine workflows
- retention policies and legal holds
- encryption-key routing by tenant
- live object-store upload and retrieval implementation
- signed evidence manifests
- proof issuance over evidence bundles
- end-user evidence UI
