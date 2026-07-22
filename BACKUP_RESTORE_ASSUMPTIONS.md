# Backup Restore Assumptions

## Purpose

This document states the minimum backup and restore assumptions for a managed single-tenant invoice payment pilot.

## Data That Must Be Covered

At minimum, backup coverage must include:

- the PostgreSQL database
- the filesystem-backed evidence storage path
- the object storage bucket or namespace used for backup copies and exports

## Minimum Backup Expectations

Before pilot go-live:

- database backups or snapshots are enabled
- evidence storage is included in a backup or snapshot process
- object storage retention is configured if it is used for copied backup material

## Restore Expectations

Restore remains a manual operator procedure in the current pilot model.

Before accepting live pilot traffic, the operating team should know:

- how to restore the database to a safe point
- how to restore the filesystem-backed evidence storage path
- how to recover backup copies from object storage if used

## What This Repo Does Not Yet Provide

- automated backup orchestration
- automated restore tooling
- disaster recovery automation
- documented recovery point or recovery time guarantees

## Why This Is Still Acceptable For The Pilot

This pass is for pilot-ready managed deployment infrastructure, not finished production operations maturity. The important requirement is that backup responsibility is explicit and not forgotten.
