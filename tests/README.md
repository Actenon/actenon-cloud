# Tests Layout

This directory holds automated tests for Actenon Cloud.

The target test split is:

- `tests/acceptance/` for high-level repository and release acceptance checks
- `tests/contract/` for open-kernel compatibility checks
- `tests/integration/` for service and persistence flows
- `tests/unit/` for local configuration and runtime unit tests

Current live tests cover:

- runtime configuration validation
- liveness endpoint behavior
- readiness endpoint behavior

`scripts/verify.sh` remains the acceptance gate and will expand over time as service coverage grows.
