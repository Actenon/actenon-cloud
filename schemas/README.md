# Schemas Layout

This directory separates schemas owned by Actenon Cloud from schemas imported or pinned from the open execution kernel.

- `schemas/control_plane/` is for repository-owned API and domain schemas
- `schemas/kernel/` is for pinned or referenced kernel artifacts

That split should remain visible to prevent boundary drift.
