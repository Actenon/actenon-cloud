# Ship Status

## Date

This status reflects the local validation run completed on April 6, 2026.

## Current Ship State

Actenon Cloud is now a pilot-stage backend-first private service for finance-focused control-plane workflows. It is beyond repo scaffold stage and beyond pure architecture documentation stage.

The repo currently implements:

- tenant and policy management
- Action Intent intake against a pinned external kernel contract
- approval workflow and evidence ingestion
- bounded proof issuance and signing abstraction
- capability escrow lifecycle tracking
- receipt ingestion, reconciliation hooks, and audit trace APIs
- basic multi-tenant admin and auth foundations
- release hygiene controls, package build smoke checks, and pilot-readiness planning documents

## Last Verified Locally

The following checks were run successfully:

- `python -m ruff check app tests scripts`
- `python -m build --sdist --wheel --outdir <temp-dir>`
- `python -m pytest -q`
- `python -m alembic upgrade head`
- `bash scripts/verify.sh`
- `bash scripts/judge.sh`

## Honest Summary

- Good for internal company development: yes
- Good for controlled design-partner pilots: potentially, with explicit cautions and dedicated operator support
- Good for real production deployment: no

See [CONTROL_PLANE_RELEASE_READINESS.md](CONTROL_PLANE_RELEASE_READINESS.md) for the readiness ratings, [BLOCKERS.md](BLOCKERS.md) for the current hard blockers, and [PILOT_ENVIRONMENT_REQUIREMENTS.md](PILOT_ENVIRONMENT_REQUIREMENTS.md) for the minimum pilot bar.
