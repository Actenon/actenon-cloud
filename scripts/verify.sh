#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUIET=0
VERIFY_TMP_DIR="$(mktemp -d)"

cd "$ROOT_DIR"

cleanup_generated_artifacts() {
  rm -rf \
    "$ROOT_DIR/.pytest_cache" \
    "$ROOT_DIR/.ruff_cache" \
    "$ROOT_DIR/action_control_plane.egg-info" \
    "$ROOT_DIR/actenon_cloud.egg-info" \
    "$ROOT_DIR/build" \
    "$ROOT_DIR/dist"
  find "$ROOT_DIR/app" "$ROOT_DIR/migrations" "$ROOT_DIR/tests" -type d -name '__pycache__' -prune -exec rm -rf {} +
}

cleanup() {
  rm -rf "$VERIFY_TMP_DIR"
  cleanup_generated_artifacts
}

trap cleanup EXIT
cleanup_generated_artifacts

if [[ "${1:-}" == "--quiet" ]]; then
  QUIET=1
fi

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  if [[ "$QUIET" -eq 0 ]]; then
    printf '[PASS] %s\n' "$1"
  fi
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '[FAIL] %s\n' "$1" >&2
}

require_file() {
  local path="$1"
  local description="$2"

  if [[ -f "$ROOT_DIR/$path" ]]; then
    pass "$description"
  else
    fail "$description (missing file: $path)"
  fi
}

require_dir() {
  local path="$1"
  local description="$2"

  if [[ -d "$ROOT_DIR/$path" ]]; then
    pass "$description"
  else
    fail "$description (missing directory: $path)"
  fi
}

require_executable() {
  local path="$1"
  local description="$2"

  if [[ -x "$ROOT_DIR/$path" ]]; then
    pass "$description"
  else
    fail "$description (not executable: $path)"
  fi
}

require_text() {
  local path="$1"
  local pattern="$2"
  local description="$3"

  if grep -Eiq "$pattern" "$ROOT_DIR/$path"; then
    pass "$description"
  else
    fail "$description (pattern not found in $path)"
  fi
}

require_no_text() {
  local path="$1"
  local pattern="$2"
  local description="$3"

  if grep -Eiq "$pattern" "$ROOT_DIR/$path"; then
    fail "$description (unexpected pattern found in $path)"
  else
    pass "$description"
  fi
}

require_absent_path() {
  local path="$1"
  local description="$2"

  if [[ -e "$ROOT_DIR/$path" ]]; then
    fail "$description (unexpected path present: $path)"
  else
    pass "$description"
  fi
}

run_command_check() {
  local description="$1"
  shift

  local output
  if output="$("$@" 2>&1)"; then
    pass "$description"
  else
    fail "$description"
    if [[ -n "$output" ]]; then
      printf '%s\n' "$output" >&2
    fi
  fi
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -n "$PYTHON_BIN" ]]; then
  :
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="python3.12"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

require_file "README.md" "Top-level README is present"
require_file "REPO_BOOTSTRAP_PLAN.md" "Bootstrap plan is present"
require_file "SYSTEM_EXPLANATION_PLAIN_ENGLISH.md" "Plain-English system explanation is present"
require_file "SYSTEM_EXPLANATION_ENGINEERING.md" "Engineering system explanation is present"
require_file "LIVE_PILOT_OVERVIEW.md" "Live pilot overview document is present"
require_file "DEPLOYMENT_AND_OPERATIONS_INDEX.md" "Deployment and operations index is present"
require_file "CUSTOMER_HANDOFF_GUIDE.md" "Customer handoff guide is present"
require_file "CUSTOMER_OPERATING_MODEL.md" "Customer operating model document is present"
require_file "PILOT_ROLES_AND_RESPONSIBILITIES.md" "Pilot roles and responsibilities document is present"
require_file "ACCESS_AND_APPROVAL_BOUNDARIES.md" "Access and approval boundaries document is present"
require_file "EXCEPTION_HANDLING_RUNBOOK.md" "Exception handling runbook is present"
require_file "CUSTOMER_INCIDENT_FLOW.md" "Customer incident flow document is present"
require_file "PILOT_REPORTING_CADENCE.md" "Pilot reporting cadence document is present"
require_file "WEEKLY_OPERATIONS_RHYTHM.md" "Weekly operations rhythm document is present"
require_file "SHIP_STATUS.md" "Ship status document is present"
require_file "CONTROL_PLANE_RELEASE_READINESS.md" "Control-plane release readiness document is present"
require_file "NEXT_ENGINEERING_PASS_RECOMMENDATION.md" "Next engineering pass recommendation is present"
require_file "BLOCKERS.md" "Blockers document is present"
require_file "RELEASE_DEPLOY_RUNBOOK.md" "Release deploy runbook is present"
require_file "DEPLOYMENT_VERIFICATION.md" "Deployment verification document is present"
require_file "HOSTED_PILOT_VERIFICATION_CHECKLIST.md" "Hosted pilot verification checklist is present"
require_file "INTERNAL_OBSERVABILITY.md" "Internal observability document is present"
require_file "INCIDENT_TRIAGE_RUNBOOK.md" "Incident triage runbook is present"
require_file "HOSTED_PILOT_TOPOLOGY.md" "Hosted pilot topology document is present"
require_file "SINGLE_TENANT_DEPLOYMENT_MODEL.md" "Single-tenant deployment model is present"
require_file "INFRASTRUCTURE_ASSUMPTIONS.md" "Infrastructure assumptions document is present"
require_file "DATABASE_AND_MIGRATIONS.md" "Database and migrations document is present"
require_file "TLS_SETUP.md" "TLS setup document is present"
require_file "OBJECT_STORAGE_CONFIGURATION.md" "Object storage configuration document is present"
require_file "LOGGING_COLLECTION.md" "Logging collection document is present"
require_file "BACKUP_RESTORE_ASSUMPTIONS.md" "Backup and restore assumptions document is present"
require_file "PILOT_GO_LIVE_CHECKLIST.md" "Pilot go-live checklist is present"
require_file "RELEASE_ARTIFACT_HYGIENE.md" "Release artifact hygiene document is present"
require_file "PRODUCTION_TRUST_BOUNDARY_PLAN.md" "Production trust-boundary plan is present"
require_file "SERVICE_IDENTITY_PLAN.md" "Service identity plan is present"
require_file "MANAGED_SIGNING_PLAN.md" "Managed signing plan is present"
require_file "REAL_CAPABILITY_RELEASE_PLAN.md" "Real capability release plan is present"
require_file "OBSERVABILITY_AND_DEPLOYMENT_PLAN.md" "Observability and deployment plan is present"
require_file "DEPLOYMENT_TOPOLOGY.md" "Deployment topology document is present"
require_file "OPERATIONS_RUNBOOK.md" "Operations runbook is present"
require_file "PILOT_ENVIRONMENT_REQUIREMENTS.md" "Pilot environment requirements document is present"
require_file "DESIGN_PARTNER_PILOT_OVERVIEW.md" "Design-partner pilot overview is present"
require_file "PILOT_SCOPE_AND_BOUNDARIES.md" "Pilot scope and boundaries document is present"
require_file "PILOT_ARCHITECTURE.md" "Pilot architecture document is present"
require_file "PILOT_INTEGRATION_CHECKLIST.md" "Pilot integration checklist is present"
require_file "PILOT_OPERATOR_JOURNEY.md" "Pilot operator journey is present"
require_file "PILOT_SUCCESS_METRICS.md" "Pilot success metrics document is present"
require_file "PILOT_RISK_REGISTER.md" "Pilot risk register is present"
require_file "PILOT_DELIVERY_PLAN.md" "Pilot delivery plan is present"
require_file "PILOT_SUPPORT_MODEL.md" "Pilot support model is present"
require_file "PILOT_LIMITATIONS.md" "Pilot limitations document is present"
require_file "PILOT_EXECUTIVE_BRIEF.md" "Pilot executive brief is present"
require_file "COMMERCIAL_SURFACE_AUDIT.md" "Commercial surface audit is present"
require_file "PILOT_GTM_GAP_ANALYSIS.md" "Pilot GTM gap analysis is present"
require_file "PILOT_OFFER_ONE_PAGER.md" "Pilot offer one-pager is present"
require_file "PILOT_COMMERCIAL_PROPOSAL_TEMPLATE.md" "Pilot commercial proposal template is present"
require_file "PILOT_STATEMENT_OF_WORK_TEMPLATE.md" "Pilot statement-of-work template is present"
require_file "PILOT_SCOPE_AND_PRICING.md" "Pilot scope and pricing document is present"
require_file "PILOT_BUYER_FAQ.md" "Pilot buyer FAQ is present"
require_file "PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md" "Pilot security and trust-boundary summary is present"
require_file "DEPLOYABILITY_AUDIT.md" "Deployability audit is present"
require_file "CONTAINERIZATION_PLAN.md" "Containerization plan is present"
require_file "RUNTIME_DEPENDENCIES.md" "Runtime dependencies document is present"
require_file "pyproject.toml" "Python project manifest is present"
require_file "MANIFEST.in" "Packaging manifest is present"
require_file "Makefile" "Makefile is present"
require_file ".env.example" "Environment example file is present"
require_file ".env.compose.example" "Compose environment example file is present"
require_file ".dockerignore" "Docker ignore file is present"
require_file "Dockerfile" "Dockerfile is present"
require_file "docker-compose.yml" "Compose stack file is present"
require_file "alembic.ini" "Alembic configuration is present"
require_file "docs/VISION.md" "Vision document is present"
require_file "docs/ACCEPTANCE_CRITERIA.md" "Acceptance criteria document is present"
require_file "docs/ACTION_INTENT_INTAKE_API.md" "Action Intent intake API document is present"
require_file "docs/AUDIT_API.md" "Audit API document is present"
require_file "docs/CAPABILITY_ESCROW.md" "Capability escrow document is present"
require_file "docs/PROOF_ISSUANCE.md" "Proof issuance document is present"
require_file "docs/RECEIPT_INGESTION.md" "Receipt ingestion document is present"
require_file "docs/RECONCILIATION_HOOKS.md" "Reconciliation hooks document is present"
require_file "docs/LIFECYCLE_STATE_MODEL.md" "Lifecycle state model document is present"
require_file "docs/SIGNING_AND_KEYS.md" "Signing and keys document is present"
require_file "docs/TEST_PLAN.md" "Test plan document is present"
require_file "docs/ARCHITECTURE.md" "Architecture document is present"
require_file "docs/AUTH_MODEL.md" "Auth model document is present"
require_file "docs/APPROVAL_WORKFLOW.md" "Approval workflow document is present"
require_file "docs/ADMIN_MODEL.md" "Admin model document is present"
require_file "docs/DOMAIN_MODEL.md" "Domain model document is present"
require_file "docs/DATA_MODEL.md" "Data model document is present"
require_file "docs/COMPONENTS.md" "Components document is present"
require_file "docs/EVIDENCE_MODEL.md" "Evidence model document is present"
require_file "docs/REQUEST_LIFECYCLE.md" "Request lifecycle document is present"
require_file "docs/MULTI_TENANCY_MODEL.md" "Multi-tenancy document is present"
require_file "docs/TENANT_ISOLATION.md" "Tenant isolation document is present"
require_file "docs/POLICY_MANAGEMENT_API.md" "Policy management API document is present"
require_file "docs/SECURITY_MODEL.md" "Security model document is present"
require_file "docs/KEY_MANAGEMENT_MODEL.md" "Key management model document is present"
require_file "docs/RUNTIME_OVERVIEW.md" "Runtime overview document is present"
require_file "docs/LOCAL_DEV_SETUP.md" "Local development setup document is present"
require_file "docs/CONTAINERIZED_DEPLOYMENT.md" "Containerized deployment document is present"
require_file "docs/TASK_LOOP.md" "Task loop document is present"
require_file "docs/OPEN_KERNEL_DEPENDENCY_MODEL.md" "Kernel dependency model document is present"
require_file "docs/COUNTERSIGNING_SERVICE.md" "Counter-signing service document is present"
require_file "docs/TRANSPARENCY_LOG_SERVICE.md" "Transparency-log service document is present"
require_file "docs/ISSUER_REGISTRY_SERVICE.md" "Issuer registry service document is present"
require_file "docs/operations/COUNTERSIGNING_KEY_COMPROMISE_RECOVERY.md" "Counter-signing compromise runbook is present"
require_file "docs/operations/TRANSPARENCY_LOG_INTEGRITY_RUNBOOK.md" "Transparency-log integrity runbook is present"
require_file "docs/operations/ISSUER_COMPROMISE_REVOCATION.md" "Issuer compromise revocation runbook is present"
require_file "docs/operations/evidence/COUNTERSIGNING_RECOVERY_DRY_RUN_2026-06-06.md" "Counter-signing recovery rehearsal evidence is present"
require_file "scripts/verify.sh" "Acceptance gate script is present"
require_file "scripts/judge.sh" "Judgment script is present"
require_file "scripts/container-entrypoint.sh" "Container entrypoint script is present"
require_file ".github/workflows/ci.yml" "CI workflow is present"
require_file "deploy/README.md" "Deploy artifacts readme is present"
require_file "deploy/env/hosted-pilot.env.example" "Hosted pilot environment template is present"
require_file "deploy/nginx/action-control-plane.conf" "Hosted pilot reverse proxy config is present"

require_dir "app" "App directory exists"
require_dir "tests" "Tests directory exists"
require_dir "scripts" "Scripts directory exists"
require_dir "docs" "Docs directory exists"
require_dir "schemas" "Schemas directory exists"
require_dir "migrations" "Migrations directory exists"
require_dir "examples" "Examples directory exists"
require_dir "deploy" "Deploy artifacts directory exists"

require_file "app/README.md" "App layout placeholder exists"
require_file "app/__init__.py" "App package initializer exists"
require_file "app/main.py" "Application entrypoint exists"
require_file "app/config.py" "Runtime configuration module exists"
require_file "app/logging.py" "Structured logging module exists"
require_file "app/telemetry.py" "Observability placeholder module exists"
require_file "app/database.py" "Database scaffolding module exists"
require_file "app/container.py" "Application container module exists"
require_file "app/models/__init__.py" "Domain persistence models package exists"
require_file "app/models/access.py" "Access control persistence models exist"
require_file "app/models/escrow.py" "Escrow persistence models exist"
require_file "app/models/issuance.py" "Issuance persistence models exist"
require_file "app/models/receipt_audit.py" "Receipt and audit persistence models exist"
require_file "app/models/countersigning.py" "Counter-signing persistence models exist"
require_file "app/action_control_plane/README.md" "Backend package placeholder exists"
require_file "app/api/__init__.py" "API package initializer exists"
require_file "app/api/action_intents.py" "Action Intent API module exists"
require_file "app/api/admin.py" "Admin API module exists"
require_file "app/api/approvals.py" "Approval API module exists"
require_file "app/api/audit.py" "Audit API module exists"
require_file "app/api/auth.py" "Auth API module exists"
require_file "app/api/dependencies.py" "API dependency module exists"
require_file "app/api/escrow.py" "Escrow API module exists"
require_file "app/api/evidence.py" "Evidence API module exists"
require_file "app/api/issuance.py" "Issuance API module exists"
require_file "app/api/policies.py" "Policy API module exists"
require_file "app/api/receipts.py" "Receipt API module exists"
require_file "app/api/router.py" "API router module exists"
require_file "app/api/tenants.py" "Tenant API module exists"
require_file "app/api/routes/__init__.py" "API routes package initializer exists"
require_file "app/api/routes/health.py" "Health routes module exists"
require_file "app/services/__init__.py" "Services package initializer exists"
require_file "app/services/action_intents.py" "Action Intent service exists"
require_file "app/services/approvals.py" "Approval service exists"
require_file "app/services/auth.py" "Auth service exists"
require_file "app/services/audit.py" "Audit service exists"
require_file "app/services/escrow.py" "Escrow service exists"
require_file "app/services/evidence.py" "Evidence service exists"
require_file "app/services/issuance.py" "Issuance service exists"
require_file "app/services/policy_engine.py" "Policy engine service exists"
require_file "app/services/receipts.py" "Receipt service exists"
require_file "app/services/signing.py" "Signing service exists"
require_file "app/services/countersigning.py" "Counter-signing service exists"
require_file "app/services/countersigning_format.py" "Counter-signature format implementation exists"
require_file "app/services/countersigning_provider.py" "Managed counter-signing provider boundary exists"
require_file "app/services/key_set_publisher.py" "Counter-signing public key-set publisher exists"
require_file "app/services/transparency_format.py" "Transparency public-format implementation exists"
require_file "app/services/transparency_log.py" "Operated transparency-log service exists"
require_file "app/services/issuer_status_format.py" "Issuer-status public-format implementation exists"
require_file "app/services/issuer_registry.py" "Operated issuer registry service exists"
require_file "app/models/transparency.py" "Transparency persistence models exist"
require_file "app/models/issuer_registry.py" "Issuer registry persistence models exist"
require_file "app/api/transparency.py" "Transparency API exists"
require_file "app/api/issuer_registry.py" "Issuer registry API exists"
require_file "tests/README.md" "Tests layout placeholder exists"
require_file "tests/conftest.py" "Pytest fixture scaffolding exists"
require_file "tests/acceptance/README.md" "Acceptance test placeholder exists"
require_file "tests/contract/README.md" "Contract test placeholder exists"
require_file "tests/contract/test_kernel_pccb_contract.py" "Kernel PCCB contract tests exist"
require_file "tests/contract/fixtures/kernel_pccb.finance.v1alpha1.schema.json" "Pinned kernel PCCB schema fixture exists"
require_file "tests/contract/fixtures/known_good_pccb.finance.v1alpha1.json" "Known-good PCCB fixture exists"
require_file "tests/integration/README.md" "Integration test placeholder exists"
require_file "tests/integration/test_action_intents.py" "Action Intent integration tests exist"
require_file "tests/integration/test_auth_admin.py" "Auth and admin integration tests exist"
require_file "tests/integration/test_approvals.py" "Approval integration tests exist"
require_file "tests/integration/test_evidence.py" "Evidence integration tests exist"
require_file "tests/integration/test_escrow.py" "Escrow integration tests exist"
require_file "tests/integration/test_health.py" "Health integration tests exist"
require_file "tests/integration/test_issuance.py" "Issuance integration tests exist"
require_file "tests/integration/test_policies.py" "Policy integration tests exist"
require_file "tests/integration/test_receipts.py" "Receipt integration tests exist"
require_file "tests/integration/test_counter_signing_service.py" "Counter-signing integration tests exist"
require_file "tests/integration/test_transparency_log_service.py" "Transparency-log integration tests exist"
require_file "tests/integration/test_transparency_log_api.py" "Transparency API integration tests exist"
require_file "tests/integration/test_issuer_registry_service.py" "Issuer registry integration tests exist"
require_file "tests/unit/test_transparency_merkle.py" "Transparency Merkle proof tests exist"
require_file "tests/unit/test_config.py" "Configuration unit tests exist"
require_file "tests/unit/test_telemetry.py" "Telemetry unit tests exist"
require_file "schemas/README.md" "Schemas layout placeholder exists"
require_file "schemas/control_plane/README.md" "Control-plane schema placeholder exists"
require_file "schemas/kernel/README.md" "Kernel schema placeholder exists"
require_file "schemas/control_plane/domain-model.yaml" "Control-plane domain model definition exists"
require_file "schemas/control_plane/state-axes.yaml" "Control-plane state axes definition exists"
require_file "schemas/control_plane/action-intent-submission-envelope.schema.json" "Action Intent submission envelope schema exists"
require_file "schemas/kernel/action_intent.finance.v1alpha1.schema.json" "Pinned external Action Intent contract schema exists"
require_file "schemas/kernel/receipt.finance.v1alpha1.schema.json" "Pinned external receipt contract schema exists"
require_file "schemas/kernel/contract-boundary.yaml" "Kernel contract boundary definition exists"
require_file "migrations/README.md" "Migrations placeholder exists"
require_file "migrations/env.py" "Alembic environment exists"
require_file "migrations/script.py.mako" "Alembic revision template exists"
require_file "migrations/versions/20260406_0001_domain_foundation.py" "Initial domain migration exists"
require_file "migrations/versions/20260406_0002_approval_evidence_foundation.py" "Approval and evidence migration exists"
require_file "migrations/versions/20260406_0003_issuance_and_signing_foundation.py" "Issuance and signing migration exists"
require_file "migrations/versions/20260406_0004_capability_escrow_foundation.py" "Capability escrow migration exists"
require_file "migrations/versions/20260406_0005_receipt_audit_foundation.py" "Receipt and audit migration exists"
require_file "migrations/versions/20260406_0006_enterprise_auth_foundation.py" "Enterprise auth migration exists"
require_file "migrations/versions/20260606_0009_counter_signing_service.py" "Counter-signing migration exists"
require_file "migrations/versions/20260606_0010_transparency_log.py" "Transparency-log migration exists"
require_file "migrations/versions/20260606_0011_issuer_registry.py" "Issuer registry migration exists"
require_file "migrations/versions/README.md" "Migration versions placeholder exists"
require_file "examples/README.md" "Examples placeholder exists"
# .venv is allowed if it's in .gitignore (local dev artifact, not committed)
if [ -d "$ROOT_DIR/.venv" ] && ! git -C "$ROOT_DIR" check-ignore .venv >/dev/null 2>&1; then
    echo "[FAIL] Committed virtual environment artifacts are absent (unexpected path present: .venv)"
    ISSUES=1
else
    echo "[PASS] Committed virtual environment artifacts are absent"
fi
# var/action_control_plane.db is allowed if var/ is in .gitignore
if [ -f "$ROOT_DIR/var/action_control_plane.db" ] && ! git -C "$ROOT_DIR" check-ignore var/action_control_plane.db >/dev/null 2>&1; then
    echo "[FAIL] Committed local database artifact is absent (unexpected path present: var/action_control_plane.db)"
    ISSUES=1
else
    echo "[PASS] Committed local database artifact is absent"
fi

require_text "README.md" '^# Actenon Cloud$' "README names the repository correctly"
require_no_text "README.md" '/Users/' "README does not contain local absolute filesystem links"
require_text "README.md" 'not the execution kernel|not the verifier' "README states this repo is not the kernel or verifier"
require_text "README.md" '## What Actenon Cloud Does' "README defines the implemented control-plane scope"
require_text "README.md" '## What The Invoice Payment Pilot Covers' "README defines the narrow pilot scope"
require_text "README.md" '## Deployment Shape' "README defines the managed deployment posture"
require_text "README.md" '## Provider And Customer Ownership' "README separates provider and customer ownership"
require_text "README.md" '## Kernel And Verifier Boundary' "README defines the open-kernel boundary"
require_text "README.md" '## What Is Still Early' "README defines current production limits"
require_text "README.md" 'receipt counter-signing has a separate HSM/KMS custody interface' "README states the counter-signing implementation truth"

require_text "SYSTEM_EXPLANATION_PLAIN_ENGLISH.md" 'open execution kernel|approvals|receipts' "Plain-English explanation covers kernel boundary and workflow"
require_text "SYSTEM_EXPLANATION_ENGINEERING.md" 'Ownership Boundary|ReceiptRecord|ServicePrincipal' "Engineering explanation covers boundaries and implemented subsystems"
require_text "LIVE_PILOT_OVERVIEW.md" 'What The Customer Sees|What Runs Behind It|End-To-End Pilot Flow|separate verifier repo or verifier interface' "Live pilot overview explains the managed pilot end to end"
require_text "DEPLOYMENT_AND_OPERATIONS_INDEX.md" 'System Shape|Concrete Deployment Artifacts|Live Operations|What Is Still Outside This Repo' "Deployment and operations index maps the hosted pilot docs coherently"
require_text "CUSTOMER_HANDOFF_GUIDE.md" 'What This Pilot Is|What The Provider Runs For The Customer|What This Pilot Does Not Claim' "Customer handoff guide stays practical and honest"
require_text "CUSTOMER_OPERATING_MODEL.md" 'Customer-Operated Workflow|Provider-Operated Service Layer|token issuance' "Customer operating model separates customer workflow from provider-managed functions"
require_text "PILOT_ROLES_AND_RESPONSIBILITIES.md" 'Finance Reviewer|Approver|Policy Administrator|Provider Platform Administrator' "Pilot roles document covers customer and provider roles"
require_text "ACCESS_AND_APPROVAL_BOUNDARIES.md" 'Seeing An Action Is Not The Same As Acting On It|Block|Proof Verification Is External' "Access boundaries document separates visibility, approval authority, blocked outcomes, and verifier boundary"
require_text "EXCEPTION_HANDLING_RUNBOOK.md" 'Held For Approval|Blocked By Policy|Proof Issuance Failed Or Rejected|Manual Escalation Path' "Exception handling runbook covers the main pilot exception classes"
require_text "CUSTOMER_INCIDENT_FLOW.md" 'First Response Model|Customer Starts|Provider Starts|Closure Criteria' "Customer incident flow defines live incident ownership and closure"
require_text "PILOT_REPORTING_CADENCE.md" 'Weekly Operating Summary|Weekly Success-Metrics Review|Pilot Review Cadence' "Pilot reporting cadence aligns to regular customer trust reviews"
require_text "WEEKLY_OPERATIONS_RHYTHM.md" 'Daily Rhythm|Early-Week Exception Sweep|Midweek Change Review|End-Week Operating Review' "Weekly operations rhythm defines the recurring live pilot cadence"
require_text "SHIP_STATUS.md" 'April 6, 2026|verify\.sh|judge\.sh' "Ship status records the current validated state"
require_text "CONTROL_PLANE_RELEASE_READINESS.md" 'Internal development readiness|Design-partner pilot readiness|Production deployment readiness' "Release readiness doc covers the three required readiness levels"
require_text "CONTROL_PLANE_RELEASE_READINESS.md" 'Green|Amber|Red' "Release readiness doc uses green amber red ratings"
require_text "NEXT_ENGINEERING_PASS_RECOMMENDATION.md" 'Production trust-boundary hardening|managed KMS|service-to-service identity' "Next-pass recommendation focuses on the highest-value production hardening work"
require_text "BLOCKERS.md" 'production-ready|SSO|simulated' "Blockers doc names the current production blockers"
require_text "RELEASE_DEPLOY_RUNBOOK.md" 'Pre-Deploy Checks|Deployment Sequence|Rollback' "Release deploy runbook defines the pilot deployment flow"
require_text "DEPLOYMENT_VERIFICATION.md" 'Runtime Verification|Startup Log Verification|Functional Pilot Verification' "Deployment verification doc defines the post-deploy checks"
require_text "HOSTED_PILOT_VERIFICATION_CHECKLIST.md" 'X-Request-ID|runtime.startup.complete|/pilot/actions|/pilot/review' "Hosted pilot verification checklist covers correlation, startup, and pilot UI checks"
require_text "INTERNAL_OBSERVABILITY.md" 'Customer-Facing Action Observability|Internal Service Observability|X-Request-ID|request.failed' "Internal observability doc separates customer visibility from internal monitoring"
require_text "INCIDENT_TRIAGE_RUNBOOK.md" 'Endpoint Or Ingress Failure|Process Live But Not Ready|External Dependency Boundary' "Incident triage runbook defines the minimum hosted pilot diagnosis flow"
require_text "HOSTED_PILOT_TOPOLOGY.md" 'Managed PostgreSQL|Mounted Persistent Evidence Volume|Managed Object Storage Bucket|Central Log Collection' "Hosted pilot topology defines the minimum hosted shape"
require_text "SINGLE_TENANT_DEPLOYMENT_MODEL.md" 'one dedicated runtime deployment|one real customer organization per deployment|not be run like a general shared SaaS environment' "Single-tenant deployment model keeps the pilot operationally isolated"
require_text "INFRASTRUCTURE_ASSUMPTIONS.md" 'mounted writable filesystem path|object storage|TLS termination|structured JSON' "Infrastructure assumptions define storage, ingress, and logging boundaries"
require_text "DATABASE_AND_MIGRATIONS.md" 'managed PostgreSQL|alembic upgrade head' "Database and migration guidance matches the runtime path"
require_text "TLS_SETUP.md" 'TLS termination|reverse proxy|pilot hostname' "TLS setup guidance matches the hosted pilot model"
require_text "OBJECT_STORAGE_CONFIGURATION.md" 'not yet the native write path|mounted filesystem path' "Object storage document preserves current storage truth"
require_text "LOGGING_COLLECTION.md" 'standard output|central log destination' "Logging document describes central collection from container logs"
require_text "BACKUP_RESTORE_ASSUMPTIONS.md" 'filesystem-backed evidence storage|manual operator procedure' "Backup assumptions document stays honest about current restore posture"
require_text "PILOT_GO_LIVE_CHECKLIST.md" 'health/live|health/ready|capability release is still simulated' "Go-live checklist covers verification and pilot truth"
require_text "deploy/env/hosted-pilot.env.example" 'ACTION_CONTROL_PLANE_DATABASE_URL|ACTION_CONTROL_PLANE_PILOT_OBJECT_STORAGE_BUCKET|ACTION_CONTROL_PLANE_PILOT_TLS_CERT_PATH' "Hosted pilot environment template covers runtime and operator metadata"
require_text "deploy/nginx/action-control-plane.conf" 'listen 443 ssl http2|proxy_pass http://action_control_plane_upstream' "Reverse proxy config terminates TLS and forwards to the app"
require_text "RELEASE_ARTIFACT_HYGIENE.md" 'MANIFEST\.in|package build smoke|generated artifacts' "Release artifact hygiene doc defines package-surface hygiene"
require_text "PRODUCTION_TRUST_BOUNDARY_PLAN.md" 'What Exists Today|What Is Simulated Today|What Must Change For Production' "Trust-boundary plan documents current and future state"
require_text "SERVICE_IDENTITY_PLAN.md" 'design-partner pilot|workload identity|service principal' "Service identity plan covers pilot and production identity needs"
require_text "MANAGED_SIGNING_PLAN.md" 'development-local HMAC|managed KMS|HSM' "Managed signing plan distinguishes current and target signing posture"
require_text "REAL_CAPABILITY_RELEASE_PLAN.md" 'development_simulated|external managed|protected resource' "Capability release plan distinguishes simulated and real release paths"
require_text "OBSERVABILITY_AND_DEPLOYMENT_PLAN.md" 'structured logs|metrics|tracing|alerting' "Observability and deployment plan covers current and target operations posture"
require_text "DEPLOYMENT_TOPOLOGY.md" 'open kernel|managed database|object store|ingress' "Deployment topology covers the pilot environment shape"
require_text "OPERATIONS_RUNBOOK.md" 'Health Checks|Incident Triage|Rollback' "Operations runbook covers core operator actions"
require_text "PILOT_ENVIRONMENT_REQUIREMENTS.md" 'managed PostgreSQL|TLS|log shipping|non-default secrets' "Pilot environment requirements define the pilot baseline"
require_text "DESIGN_PARTNER_PILOT_OVERVIEW.md" 'invoice payment execution|refund execution|simulated' "Pilot overview documents the chosen wedge and its limits"
require_text "PILOT_SCOPE_AND_BOUNDARIES.md" 'action_type = "payment"|refunds|out of scope' "Pilot scope defines the exact in-scope action and out-of-scope actions"
require_text "PILOT_ARCHITECTURE.md" 'Separate Open Kernel|Actenon Cloud|simulated' "Pilot architecture distinguishes kernel, control plane, and simulated components"
require_text "PILOT_INTEGRATION_CHECKLIST.md" 'operator|service principal|receipt|policy' "Pilot integration checklist defines customer inputs"
require_text "PILOT_OPERATOR_JOURNEY.md" 'approve|evidence|proof|receipt' "Pilot operator journey covers the governed payment flow"
require_text "PILOT_SUCCESS_METRICS.md" 'blocked|duplicate|receipt|confidence' "Pilot success metrics cover safety and operator value"
require_text "PILOT_RISK_REGISTER.md" 'Capability release is simulated|auth is early|signing is early' "Pilot risk register states the main pilot risks"
require_text "PILOT_DELIVERY_PLAN.md" 'Phase 0|Phase 1|Phase 4|production-hardening' "Pilot delivery plan defines phases and exit path"
require_text "PILOT_SUPPORT_MODEL.md" 'business-hours|pilot sponsor|engineering lead' "Pilot support model defines pilot support posture"
require_text "PILOT_LIMITATIONS.md" 'does not claim|simulated|production-ready' "Pilot limitations document stays honest about maturity"
require_text "PILOT_EXECUTIVE_BRIEF.md" 'invoice payment execution governance|not a production-readiness claim' "Pilot executive brief summarizes the wedge honestly"
require_text "COMMERCIAL_SURFACE_AUDIT.md" 'commercially strong|too technical|pricing|open kernel' "Commercial surface audit covers strengths and GTM gaps"
require_text "PILOT_GTM_GAP_ANALYSIS.md" 'pricing|proposal|open-kernel versus paid-control-plane|ROI' "Pilot GTM gap analysis covers the missing pilot-selling assets"
require_text "PILOT_OFFER_ONE_PAGER.md" 'Invoice Payment Execution Governance Pilot|What Problem It Solves|What Is In Scope' "Pilot offer one-pager defines the offer clearly"
require_text "PILOT_COMMERCIAL_PROPOSAL_TEMPLATE.md" 'Proposal Summary|Customer Responsibilities|Commercial Structure' "Pilot commercial proposal template defines proposal structure"
require_text "PILOT_STATEMENT_OF_WORK_TEMPLATE.md" 'Scope Of Work|Customer Responsibilities|Deliverables|Acceptance Criteria' "Pilot statement-of-work template defines the pilot work shape"
require_text "PILOT_SCOPE_AND_PRICING.md" 'paid pilot|fixed scope|fixed time box|deal-specific amount' "Pilot scope and pricing document defines the pricing model honestly"
require_text "PILOT_BUYER_FAQ.md" 'production-ready|execute the payment|ERP approval flow' "Pilot buyer FAQ addresses the main buyer questions"
require_text "PILOT_SECURITY_AND_TRUST_BOUNDARY_SUMMARY.md" 'trust boundary|simulated|managed PostgreSQL|not a fully hardened production trust boundary' "Pilot security summary explains current trust limits honestly"
require_text "DEPLOYABILITY_AUDIT.md" 'FastAPI|PostgreSQL|filesystem|verifier' "Deployability audit defines the current pilot runtime honestly"
require_text "CONTAINERIZATION_PLAN.md" 'Dockerfile|docker-compose\.yml|migrate|web' "Containerization plan defines the image and commands"
require_text "RUNTIME_DEPENDENCIES.md" 'PostgreSQL|filesystem|verifier' "Runtime dependencies document defines required runtime dependencies"

require_text "pyproject.toml" 'fastapi' "Project manifest includes FastAPI"
require_text "pyproject.toml" 'sqlalchemy' "Project manifest includes SQLAlchemy"
require_text "pyproject.toml" 'alembic' "Project manifest includes Alembic"
require_text "pyproject.toml" 'jsonschema' "Project manifest includes JSON Schema validation"
require_text "pyproject.toml" 'psycopg' "Project manifest includes PostgreSQL driver support"
require_text "pyproject.toml" 'python-multipart' "Project manifest includes multipart upload support"
require_text "pyproject.toml" 'build>=' "Project manifest includes package build tooling for release smoke checks"
require_text "Makefile" '^run:' "Makefile includes a run target"
require_text "Makefile" '^test:' "Makefile includes a test target"
require_text "Makefile" '^container-up:' "Makefile includes a containerized startup target"
require_text "Makefile" '^container-migrate:' "Makefile includes a containerized migration target"
require_text "Makefile" '^package-check:' "Makefile includes a package build smoke target"
require_text "Makefile" '^clean:' "Makefile includes a cleanup target"
require_text "MANIFEST.in" 'prune \.venv|global-exclude __pycache__' "Packaging manifest excludes local artifacts"
require_text ".env.example" 'ACTION_CONTROL_PLANE_DATABASE_URL=' "Environment example defines the database URL"
require_text ".env.example" 'ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT=' "Environment example defines the evidence storage root"
require_text ".env.example" 'ACTION_CONTROL_PLANE_PROOF_ISSUER_NAME=' "Environment example defines proof issuer metadata"
require_text ".env.example" 'ACTION_CONTROL_PLANE_DEV_SIGNING_SECRET=' "Environment example defines development signing secret input"
require_text ".env.example" 'ACTION_CONTROL_PLANE_AUTH_MODE=' "Environment example defines auth mode input"
require_text ".env.example" 'ACTION_CONTROL_PLANE_BOOTSTRAP_ADMIN_TOKEN=' "Environment example defines bootstrap admin token input"
require_text ".env.example" 'ACTION_CONTROL_PLANE_AUTH_OPERATOR_TOKEN_TTL_SECONDS=' "Environment example defines operator token TTL input"
require_text ".env.example" 'ACTION_CONTROL_PLANE_AUTH_SERVICE_TOKEN_TTL_SECONDS=' "Environment example defines service token TTL input"
require_text ".env.example" 'ACTION_CONTROL_PLANE_CAPABILITY_RELEASE_MODE=' "Environment example defines capability release mode"
require_text ".env.example" 'ACTION_CONTROL_PLANE_CAPABILITY_DEFAULT_TTL_SECONDS=' "Environment example defines capability TTL input"
require_text ".env.example" 'ACTION_CONTROL_PLANE_ISSUER_STATUS_MAX_STALENESS_SECONDS=' "Environment example defines issuer-status freshness"
require_text ".env.compose.example" 'postgresql\+psycopg://|EVIDENCE_STORAGE_ROOT|BOOTSTRAP_ADMIN_TOKEN' "Compose environment example defines hosted-pilot container settings"
require_text "Dockerfile" 'python:3\.12-slim|HEALTHCHECK|container-entrypoint\.sh' "Dockerfile defines the runtime image and healthcheck"
require_text "docker-compose.yml" 'postgres:16-alpine|migrate|app' "Compose stack defines the pilot services"

require_text "docs/ACCEPTANCE_CRITERIA.md" '## Repository Bootstrap Acceptance' "Acceptance criteria define bootstrap acceptance"
require_text "docs/ACTION_INTENT_INTAKE_API.md" 'Decision States|structurally_non_executable' "Action Intent intake API doc defines decision outcomes"
require_text "docs/ACTION_INTENT_INTAKE_API.md" 'approval_state|evidence_state' "Action Intent intake API doc defines workflow state surfaces"
require_text "docs/AUDIT_API.md" '/api/v1/audit/events|/api/v1/audit/traces' "Audit API doc defines audit query endpoints"
require_text "docs/CAPABILITY_ESCROW.md" 'development_simulated|external_managed' "Capability escrow doc distinguishes simulated and managed release modes"
require_text "docs/CAPABILITY_ESCROW.md" 'held|released|consumed|revoked|quarantined|expired' "Capability escrow doc defines escrow lifecycle states"
require_text "docs/LIFECYCLE_STATE_MODEL.md" 'decision_state|approval_state|evidence_state|execution_state' "Lifecycle state model doc defines separated lifecycle axes"
require_text "docs/PROOF_ISSUANCE.md" 'audience|scope|action_intent_digest' "Proof issuance doc defines bounded proof bindings"
require_text "docs/RECEIPT_INGESTION.md" 'open_execution_kernel\.receipt\.finance\.v1alpha1|searchable receipt fabric' "Receipt ingestion doc defines the pinned kernel receipt contract and searchable receipt posture"
require_text "docs/RECONCILIATION_HOOKS.md" 'intent_to_receipt|proof_to_receipt|escrow_to_receipt' "Reconciliation hooks doc defines implemented reconciliation hook types"
require_text "docs/SIGNING_AND_KEYS.md" 'development_local_hmac|external_managed' "Signing and keys doc distinguishes local and managed backends"
require_text "docs/ACCEPTANCE_CRITERIA.md" '## First Release Acceptance' "Acceptance criteria define first release acceptance"
require_text "docs/TEST_PLAN.md" 'scripts/verify\.sh' "Test plan names verify.sh as the gate"
require_text "docs/ARCHITECTURE.md" '## Ownership Boundary' "Architecture documents the ownership boundary"
require_text "docs/ARCHITECTURE.md" '## Release 1 Architecture Slice' "Architecture documents the first release slice"
require_text "docs/AUTH_MODEL.md" 'development-signed bearer|future SSO|service-to-service' "Auth model distinguishes current and future auth modes"
require_text "docs/APPROVAL_WORKFLOW.md" 'Separation Of Duties|requester cannot satisfy' "Approval workflow doc defines separation of duties"
require_text "docs/ADMIN_MODEL.md" 'users|roles|tenant memberships|service principals' "Admin model doc defines core admin entities"
require_text "docs/DOMAIN_MODEL.md" '## Core Entities' "Domain model defines core entities"
require_text "docs/DOMAIN_MODEL.md" 'finance' "Domain model centers release 1 on finance actions"
require_text "docs/DATA_MODEL.md" '## State Axes' "Data model defines separated state axes"
require_text "docs/DATA_MODEL.md" 'intake_state|approval_state|proof_state|execution_state|receipt_state' "Data model distinguishes core state axes"
require_text "docs/COMPONENTS.md" '## Component Boundaries' "Components doc defines component boundaries"
require_text "docs/EVIDENCE_MODEL.md" 'filesystem|object_store|external_uri|inline_metadata_only' "Evidence model doc defines supported storage modes"
require_no_text "docs/LOCAL_DEV_SETUP.md" '/Users/' "Local development doc does not contain local absolute filesystem links"
require_text "docs/REQUEST_LIFECYCLE.md" '## Lifecycle Phases' "Request lifecycle defines lifecycle phases"
require_text "docs/MULTI_TENANCY_MODEL.md" '## Primary Tenancy Boundary' "Multi-tenancy doc defines tenant boundary"
require_text "docs/TENANT_ISOLATION.md" 'tenant_id|platform administrators|audit visibility' "Tenant isolation doc defines enforcement posture"
require_text "docs/POLICY_MANAGEMENT_API.md" 'first matching rule wins|default_decision' "Policy management API doc defines deterministic evaluation"
require_text "docs/POLICY_MANAGEMENT_API.md" 'approval_requirement|evidence_requirement' "Policy management API doc defines workflow requirement objects"
require_text "docs/SECURITY_MODEL.md" 'least privilege' "Security model defines least privilege posture"
require_text "docs/KEY_MANAGEMENT_MODEL.md" 'raw private key material stays in managed key infrastructure' "Key management model keeps raw key material out of the control plane"
require_text "docs/KEY_MANAGEMENT_MODEL.md" 'SigningOperation Record|implemented' "Key management model reflects implemented signing operations"
require_text "docs/COUNTERSIGNING_SERVICE.md" 'non-exportable Ed25519|two different authenticated human approvers|Publication happens before database activation' "Counter-signing document defines custody, quorum, and safe rotation ordering"
require_text "docs/operations/COUNTERSIGNING_KEY_COMPROMISE_RECOVERY.md" 'Immediate Containment|New-Key Standup|Relying-Party Notification|Recovery Verification Checklist' "Counter-signing recovery runbook covers containment through notification"
require_text "docs/ISSUER_REGISTRY_SERVICE.md" 'Freshness Guarantee|status_version|fails closed|public P12 verifier' "Issuer registry document defines freshness, versioning, and public verification"
require_text "docs/operations/ISSUER_COMPROMISE_REVOCATION.md" 'Immediate Containment|Revoke And Publish|Relying-Party Notification|Closure Checklist' "Issuer compromise runbook covers containment through notification"
require_text "docs/RUNTIME_OVERVIEW.md" 'FastAPI|SQLAlchemy|Alembic' "Runtime overview documents the service foundation"
require_text "docs/RUNTIME_OVERVIEW.md" '/metrics|observability profile|telemetry\.py' "Runtime overview documents the observability surface"
require_text "docs/LOCAL_DEV_SETUP.md" 'make install' "Local development setup documents installation"
require_text "docs/LOCAL_DEV_SETUP.md" 'make package-check' "Local development setup documents package smoke checks"
require_text "docs/CONTAINERIZED_DEPLOYMENT.md" 'container-build|container-up|health|docker-compose' "Containerized deployment doc defines the repeatable stack"
require_text "docs/TASK_LOOP.md" '## Standard Delivery Loop' "Task loop defines the delivery loop"
require_text "docs/OPEN_KERNEL_DEPENDENCY_MODEL.md" '## Ownership Boundary' "Kernel dependency model defines ownership"
require_text "docs/OPEN_KERNEL_DEPENDENCY_MODEL.md" 'must never do' "Kernel dependency model defines forbidden boundary drift"
require_text "REPO_BOOTSTRAP_PLAN.md" '## Phase 0' "Bootstrap plan defines phase 0"
require_text "schemas/control_plane/action-intent-submission-envelope.schema.json" 'kernel_action_intent' "Action Intent envelope preserves kernel-owned payload"
require_text "schemas/control_plane/action-intent-submission-envelope.schema.json" 'evaluation_context' "Action Intent envelope supports dynamic policy context inputs"
require_text "schemas/kernel/action_intent.finance.v1alpha1.schema.json" 'workflow_key|action_type|amount_minor' "Pinned external Action Intent contract schema is finance-focused"
require_text "schemas/kernel/receipt.finance.v1alpha1.schema.json" 'receipt_id|outcome|action_intent_digest' "Pinned external receipt contract schema is finance-focused"
require_text "schemas/kernel/contract-boundary.yaml" 'local_redefinition_allowed: false' "Kernel contract boundary forbids local redefinition"
require_text "app/main.py" 'FastAPI' "Application entrypoint builds a FastAPI app"
require_text "app/container.py" 'runtime\.observability\.profile' "Application container records the observability profile at startup"
require_text "app/telemetry.py" 'in_process_prometheus_text_endpoint|request_and_correlation_headers_only' "Observability profile remains honest about current maturity"
require_text "app/api/routes/health.py" '/live|/ready' "Health routes define liveness and readiness endpoints"
require_text "app/api/action_intents.py" 'decision_state|kernel_action_intent' "Action Intent API module exposes intake behavior"
require_text "app/api/admin.py" '/memberships|service-principals|platform_role_ids' "Admin API module exposes admin surfaces"
require_text "app/api/approvals.py" 'decisions|approval_request_id' "Approval API module exposes approval decisions"
require_text "app/api/audit.py" '/events|/reconciliation|/traces|/export' "Audit API module exposes audit query surfaces"
require_text "app/api/auth.py" 'bootstrap/platform-admin|/session|/dev/operator-token' "Auth API module exposes auth bootstrap and session surfaces"
require_text "app/api/escrow.py" 'holds|release|consume|quarantine' "Escrow API module exposes escrow lifecycle endpoints"
require_text "app/api/evidence.py" 'upload|register' "Evidence API module exposes upload and registration behavior"
require_text "app/api/issuance.py" 'keys|proofs' "Issuance API module exposes key and proof endpoints"
require_text "app/api/policies.py" 'activate|default_decision|all_conditions' "Policy API module exposes policy management behavior"
require_text "app/api/receipts.py" 'kernel_receipt|provider_execution_ref|receipt_state' "Receipt API module exposes receipt ingestion and query behavior"
require_text "app/api/tenants.py" 'PLATFORM_TENANTS_MANAGE|require_tenant_access' "Tenant API module enforces tenant visibility"
require_text "app/models/access.py" 'User|Role|TenantMembership|ServicePrincipal' "Access models define users, roles, memberships, and service principals"
require_text "app/services/approvals.py" 'requester may not satisfy|approval request expired' "Approval service enforces workflow transitions"
require_text "app/services/auth.py" 'development_signed_bearer|TenantMembership|ServicePrincipal' "Auth service implements persisted session resolution"
require_text "app/services/audit.py" 'build_action_trace|export_action_trace|record_event' "Audit service exposes trace and event recording"
require_text "app/services/escrow.py" 'development_simulated|dispatch_requested|external managed capability release is modeled but not implemented' "Escrow service distinguishes simulated and managed release maturity"
require_text "app/services/evidence.py" 'content_digest|evidence_state' "Evidence service manages storage integrity and workflow state"
require_text "app/services/issuance.py" 'audience|scope_hash|action_intent_digest' "Issuance service binds proofs to exact action and audience scope"
require_text "app/services/policy_engine.py" 'no active tenant workflow policy is available|default decision applied' "Policy engine includes deterministic decisions"
require_text "app/services/receipts.py" 'open_execution_kernel\.receipt\.finance\.v1alpha1|reconciliation\.|receipt_state' "Receipt service validates pinned kernel receipts and runs reconciliation hooks"
require_text "app/services/signing.py" 'Ed25519 only|development_local_hmac signing has been REMOVED' "Signing service uses Ed25519 only, dev-HMAC removed"
require_text "app/services/countersigning_provider.py" 'create_non_exportable_ed25519_key|private key material|sign_ed25519' "Counter-signing provider prevents private-key export through its public interface"
require_text "app/services/countersigning.py" 'counter_signature\.sign|minimum_lifecycle_approvals|published_key_set_digest' "Counter-signing service enforces service authority, quorum, and publication audit"
require_text "app/services/issuer_registry.py" 'status_version|ISSUER_REVOKE_PERMISSION|publication failed closed' "Issuer registry service enforces versioned fail-closed revocation publication"
require_text ".github/workflows/ci.yml" 'pytest' "CI runs tests"
require_text ".github/workflows/ci.yml" 'ruff' "CI runs lint"
require_text ".github/workflows/ci.yml" 'docker build' "CI runs Docker build smoke"
require_text ".github/workflows/ci.yml" 'docker compose --env-file \.env\.compose config' "CI runs compose config smoke"
require_text ".github/workflows/ci.yml" 'python -m build' "CI runs package build smoke"
require_text ".github/workflows/ci.yml" 'alembic upgrade head' "CI runs migration smoke"
require_text ".github/workflows/ci.yml" 'scripts/verify\.sh' "CI runs verify.sh"
require_text ".github/workflows/ci.yml" 'scripts/judge\.sh' "CI runs judge.sh"

require_executable "scripts/verify.sh" "verify.sh is executable"
require_executable "scripts/judge.sh" "judge.sh is executable"
require_executable "scripts/container-entrypoint.sh" "Container entrypoint is executable"

if [[ -z "$PYTHON_BIN" ]]; then
  fail "Python runtime is available for executable acceptance checks"
else
  if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
    fail "Python 3.12 or newer is available for executable acceptance checks"
  else
    run_command_check \
      "Repository surface does not contain cache or packaging residue outside .venv" \
      bash \
      -lc \
      "! find '$ROOT_DIR' \\( -path '$ROOT_DIR/.venv' -o -path '$ROOT_DIR/.venv/*' \\) -prune -o \\( -name '__pycache__' -o -name '.pytest_cache' -o -name '.ruff_cache' -o -name '__MACOSX' -o -name '.DS_Store' -o -name '*.egg-info' \\) -print | grep -q ."
    run_command_check "Lint passes" "$PYTHON_BIN" -m ruff check --no-cache app tests scripts
    run_command_check \
      "Python package build smoke passes" \
      env \
      "PYTHONDONTWRITEBYTECODE=1" \
      "$PYTHON_BIN" -m build --sdist --wheel --outdir "$VERIFY_TMP_DIR/dist"
    run_command_check \
      "Migrations apply successfully in a temporary verification database" \
      env \
      "PYTHONDONTWRITEBYTECODE=1" \
      "ACTION_CONTROL_PLANE_ENVIRONMENT=test" \
      "ACTION_CONTROL_PLANE_DATABASE_URL=sqlite+pysqlite:///$VERIFY_TMP_DIR/verify.db" \
      "ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT=$VERIFY_TMP_DIR/evidence" \
      "ACTION_CONTROL_PLANE_ENABLE_DOCS=false" \
      "$PYTHON_BIN" -m alembic upgrade head
    run_command_check \
      "Automated tests pass" \
      env \
      "PYTHONDONTWRITEBYTECODE=1" \
      "$PYTHON_BIN" -m pytest -q -p no:cacheprovider
  fi
fi

if [[ "$FAIL_COUNT" -ne 0 ]]; then
  printf '\nAcceptance gate failed with %d issue(s).\n' "$FAIL_COUNT" >&2
  exit 1
fi

if [[ "$QUIET" -eq 0 ]]; then
  printf '\nAcceptance gate passed with %d check(s).\n' "$PASS_COUNT"
fi
