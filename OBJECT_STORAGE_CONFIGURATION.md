# Object Storage Configuration

## Purpose

This document defines the minimum object storage expectations for a managed single-tenant invoice payment pilot.

## What Object Storage Is Used For Today

Object storage is part of the hosted pilot environment for:

- backup copies
- export bundles
- manual evidence backup or replication support
- future storage hardening support

## What Object Storage Does Not Do Today

Object storage is not yet the native write path for uploaded evidence in the current runtime.

The application currently writes uploaded evidence to a mounted filesystem path defined by `ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT`.

The repo now includes an explicit object-store adapter path and configuration surface, but that adapter is still a stub. It exists to define the upgrade seam clearly, not to claim that live object-store evidence handling is complete.

Until end-to-end object-store upload and retrieval are implemented, hosted deployments should still treat the filesystem evidence root as the live evidence path.

Relevant runtime settings are:

- `ACTION_CONTROL_PLANE_EVIDENCE_UPLOAD_BACKEND`
- `ACTION_CONTROL_PLANE_EVIDENCE_OBJECT_STORE_BUCKET`
- `ACTION_CONTROL_PLANE_EVIDENCE_OBJECT_STORE_PREFIX`
- `ACTION_CONTROL_PLANE_EVIDENCE_OBJECT_STORE_ENDPOINT`

## Minimum Configuration

Provision one dedicated bucket or namespace per hosted pilot with:

- private access only
- server-side encryption if the platform offers it
- a pilot-specific prefix or namespace
- credentials scoped only to the pilot environment

Suggested operator metadata values are included in:

- `deploy/env/hosted-pilot.env.example`

## Access Model

Use object storage credentials only in the operator environment that performs:

- backup copy jobs
- export archival
- manual restore support
- future object-store backend rollout work

Do not claim that the current application runtime is already using this bucket for live evidence writes.

## Go-Live Expectations

Before pilot go-live, confirm:

- the bucket or namespace exists
- the bucket is not public
- pilot operators know which data is copied there and which data is still filesystem-backed
- backup tooling or manual procedures can write to it

## Current Limits

- the object-store adapter is present only as a narrow interface stub
- live object-store upload is not implemented in the current runtime
- object-store content retrieval is not implemented in the current runtime
- no automatic backup copier is implemented in the repo
- restore from object storage remains an operator-managed procedure
