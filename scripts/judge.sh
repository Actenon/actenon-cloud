#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY_SCRIPT="$ROOT_DIR/scripts/verify.sh"

TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

if "$VERIFY_SCRIPT" --quiet >"$TMP_OUTPUT" 2>&1; then
  OVERALL="PASS"
else
  OVERALL="FAIL"
fi

printf 'Actenon Cloud Spec Judgment\n'
printf '=================================\n'
printf 'Overall: %s\n' "$OVERALL"
printf 'Source of truth gate: scripts/verify.sh\n'

if [[ "$OVERALL" == "PASS" ]]; then
  printf '\n'
  printf 'Summary\n'
  printf -- '- Ship-status, release-readiness, blockers, release-hygiene, and system-explanation documents are present\n'
  printf -- '- Live pilot overview, customer handoff guide, and deployment-operations index are present\n'
  printf -- '- Customer operating model, pilot roles, and approval-boundary docs are present for managed pilot use\n'
  printf -- '- Exception handling, incident flow, reporting cadence, and weekly operating rhythm are documented for live pilot operation\n'
  printf -- '- Deploy and verification runbooks are present for the managed pilot runtime path\n'
  printf -- '- Internal observability, hosted verification, and incident-triage docs are present for live pilot operation\n'
  printf -- '- Hosted topology, single-tenant deployment model, and infrastructure assumptions are documented\n'
  printf -- '- Hosted pilot environment, ingress, TLS, database, logging, storage, backup, and go-live artifacts are documented\n'
  printf -- '- Required repository scaffold is present\n'
  printf -- '- Package-surface hygiene rules, cleanup tooling, and build-smoke checks are in place\n'
  printf -- '- A narrow design-partner pilot package is documented around the strongest finance-control wedge\n'
  printf -- '- Commercial-surface and pilot-GTM gap analyses are documented\n'
  printf -- '- Commercial one-pager, proposal template, SOW template, pricing model, buyer FAQ, and pilot trust summary are documented\n'
  printf -- '- Control-plane versus open-kernel ownership is documented\n'
  printf -- '- Core domain entities, state axes, and lifecycle boundaries are defined\n'
  printf -- '- Backend runtime foundation, health surfaces, local tooling, and local validation path are in place\n'
  printf -- '- A repeatable single-tenant containerized deployment path is scaffolded for managed pilot operation\n'
  printf -- '- Trust-boundary, service-identity, signing, capability-release, observability, and deployment plans are documented\n'
  printf -- '- Pilot overview, scope, architecture, operator journey, success metrics, risk register, delivery plan, and support model are documented\n'
  printf -- '- Finance-focused Action Intent intake and deterministic policy APIs are implemented\n'
  printf -- '- Approval workflow and evidence intake services are implemented and tested\n'
  printf -- '- Bounded proof issuance and development signing foundations are implemented and tested\n'
  printf -- '- Capability escrow and execution lifecycle controls are implemented and tested\n'
  printf -- '- Receipt ingestion, audit query surfaces, and reconciliation hooks are implemented and tested\n'
  printf -- '- Multi-tenant admin, development auth, and tenant-isolation foundations are implemented and tested\n'
  printf -- '- Lint, package build smoke, migration smoke, and automated tests pass under verify.sh\n'
  printf -- '- Backend-first posture and narrow first release scope are defined\n'
  printf -- '- Acceptance harness scripts are in place and executable\n'
else
  printf '\n'
  printf 'Verification output\n'
  cat "$TMP_OUTPUT"
  exit 1
fi
