# Release Artifact Hygiene

## Purpose

This document defines the hygiene rules for the repository and Python package surface of Actenon Cloud.

## What Exists Today

- `.gitignore` excludes local virtual environments, caches, coverage output, editor residue, build output, macOS residue, and egg metadata.
- `MANIFEST.in` prunes local development artifacts from source distributions.
- `make clean` removes common generated artifacts from the working tree.
- `make package-check` builds an sdist and wheel into a temporary directory without polluting the repo.
- CI runs a package build smoke step.
- `scripts/verify.sh` rejects cache or packaging residue outside `.venv`.

## Generated Artifacts That Must Not Be Committed

- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.mypy_cache/`
- `*.egg-info/`
- `build/`
- `dist/`
- `__MACOSX/`
- `.DS_Store`
- local SQLite databases and log output

## Package-Surface Rules

- Package builds must succeed from the checked-in source tree.
- Generated local state must not change what gets included in the package.
- Local development artifacts under `var/` must never ship inside build artifacts.
- The repo must remain installable with `pip install -e .[dev]`.

## Pilot Versus Production

For a design-partner pilot, the current hygiene controls are good enough to keep the repo and package surface clean for internal distribution.

For production, additional release controls are still needed:

- signed release artifacts
- private artifact publication workflow
- reproducible versioning and changelog discipline
- vulnerability scanning and dependency review gates
- provenance or attestation on released artifacts
