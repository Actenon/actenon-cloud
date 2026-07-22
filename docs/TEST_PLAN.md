# Test Plan

## Purpose

This test plan explains how Actenon Cloud validates itself today and what still needs to be added as the service moves from internal development into pilot and production hardening.

## Current Gate

`scripts/verify.sh` is the required acceptance gate. It currently proves:

- required files and directories exist
- the repository documents the control-plane versus kernel boundary
- the first release scope is explicitly defined
- release-readiness and blockers documentation exists
- lint passes
- migrations apply successfully in a temporary SQLite environment
- automated tests pass
- `scripts/judge.sh` exists and is executable

`scripts/judge.sh` is not the source of truth. It is a readable summary built on top of `scripts/verify.sh`.

## Test Layers Still To Add

### Unit Tests

- Domain rules for tenancy, policy evaluation, approval transitions, receipt indexing, and revocation logic
- Validation of repo-owned request and response schemas
- Error mapping and audit event creation

### Contract Tests

- Compatibility against pinned kernel artifacts
- Validation that kernel receipt and proof schemas are consumed without local semantic drift
- Backward compatibility checks for repo-owned control-plane APIs

### Integration Tests

- Intake API through persistence and audit emission
- Approval workflow state transitions across policy, evidence, and receipt dependencies
- Evidence metadata plus filesystem-backed upload and external registration paths
- Receipt ingestion and query behavior against realistic datasets

### Security And Authorization Tests

- Tenant isolation enforcement on read and write operations
- Role and permission boundaries
- Secret and key handling paths
- Revocation and quarantine controls

### Operational Tests

- Health checks for required dependencies
- Failure injection for storage, queue, or kernel connectivity issues
- Export generation reliability and audit completeness
- Logging and observability assertions for key workflows

## Minimum CI Evolution

The current CI path should run:

- install
- lint
- migration smoke
- unit and integration test suites
- `scripts/verify.sh`
- `scripts/judge.sh`

The next CI expansion should add:

- schema validation checks
- contract compatibility tests against pinned kernel artifacts
- basic security checks for secrets and unsafe defaults
- API compatibility tests for design-partner contracts

The acceptance gate should remain a single entrypoint even if it calls other tools underneath.

## Evidence Required For Release Decisions

Release readiness should eventually require the following evidence:

- passing acceptance gate output from `scripts/verify.sh`
- passing automated test suites
- kernel compatibility report for the pinned artifact version
- migration validation results
- audit and export sample verification
- security review for key and revocation paths

## Known Unknowns

The exact contract-test mechanism depends on how the open execution kernel publishes schemas, interfaces, and compatibility metadata. Until that is validated, this plan defines the shape of testing rather than the final tooling.
