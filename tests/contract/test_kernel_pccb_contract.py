from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.config import DEFAULT_DEV_SIGNING_SECRET, Settings
from app.services.signing import canonical_json

FIXTURES_DIR = Path(__file__).with_name("fixtures")
PCCB_SCHEMA_PATH = FIXTURES_DIR / "kernel_pccb.finance.v1alpha1.schema.json"
KNOWN_GOOD_PCCB_PATH = FIXTURES_DIR / "known_good_pccb.finance.v1alpha1.json"


@dataclass(slots=True)
class ContractVerificationResult:
    accepted: bool
    reason_code: str | None
    errors: list[str]


@lru_cache
def load_json_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def pccb_validator() -> Draft202012Validator:
    schema = load_json_fixture(PCCB_SCHEMA_PATH)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def format_validation_errors(errors: list[Any]) -> list[str]:
    formatted_errors: list[str] = []
    for error in errors:
        location = ".".join(str(segment) for segment in error.absolute_path)
        if location:
            formatted_errors.append(f"{location}: {error.message}")
        else:
            formatted_errors.append(error.message)
    return formatted_errors


def expected_signature(payload: dict[str, Any], *, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def verify_pccb_artifact(
    artifact: dict[str, Any],
    *,
    secret: str,
) -> ContractVerificationResult:
    payload = artifact.get("proof_payload")
    if not isinstance(payload, dict):
        return ContractVerificationResult(
            accepted=False,
            reason_code="artifact_shape_invalid",
            errors=["proof_payload must be a JSON object"],
        )

    validation_errors = sorted(
        pccb_validator().iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if validation_errors:
        return ContractVerificationResult(
            accepted=False,
            reason_code="schema_validation_failed",
            errors=format_validation_errors(validation_errors),
        )

    algorithm = artifact.get("algorithm")
    if algorithm != "HS256":
        return ContractVerificationResult(
            accepted=False,
            reason_code="unsupported_algorithm",
            errors=[f"unsupported algorithm '{algorithm}'"],
        )

    payload_digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    if artifact.get("proof_payload_digest") != payload_digest:
        return ContractVerificationResult(
            accepted=False,
            reason_code="payload_digest_mismatch",
            errors=["proof_payload_digest does not match the canonical payload digest"],
        )

    signature = artifact.get("signature")
    if not isinstance(signature, str) or not signature:
        return ContractVerificationResult(
            accepted=False,
            reason_code="signature_missing",
            errors=["signature must be present for verification"],
        )

    if signature != expected_signature(payload, secret=secret):
        return ContractVerificationResult(
            accepted=False,
            reason_code="signature_verification_failed",
            errors=[
                "signature does not match the canonical payload under the expected verifier key"
            ],
        )

    return ContractVerificationResult(accepted=True, reason_code=None, errors=[])


def create_tenant(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/tenants",
        json={"display_name": "Contract Test Tenant", "finance_profile": "payments"},
    )
    assert response.status_code == 201
    return response.json()


def create_allow_policy(client: TestClient, tenant_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/policies",
        json={
            "tenant_id": tenant_id,
            "name": "Contract Allow Policy",
            "description": "Simple allow policy for contract tests",
            "workflow_key": "payments.standard",
            "finance_action_classes": ["payment", "transfer"],
            "default_decision": "allow",
            "rules": [],
        },
    )
    assert response.status_code == 201
    policy = response.json()
    activate_response = client.post(f"/api/v1/policies/{policy['policy_id']}/activate")
    assert activate_response.status_code == 200
    return activate_response.json()


def create_signing_key(client: TestClient, tenant_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/issuance/keys",
        json={
            "tenant_id": tenant_id,
            "display_name": "Contract PCCB Key",
            "key_purpose": "pccb_signing",
            "algorithm": "HS256",
            "key_backend": "development_local_hmac",
            "is_default": True,
            "lifecycle_metadata": {"owner": "contract-tests"},
        },
    )
    assert response.status_code == 201
    return response.json()


def build_intake_payload(tenant_id: str, *, suffix: str = "001") -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "submission_id": f"contract-submission-{suffix}",
        "idempotency_key": f"contract-idempotency-key-{suffix}",
        "requested_by": {
            "principal_type": "user",
            "principal_id": "contract-requester-001",
        },
        "kernel_contract_ref": {
            "contract_family": "action_intent",
            "version_ref": "open_execution_kernel.action_intent.finance.v1alpha1",
        },
        "kernel_action_intent": {
            "intent_id": f"contract-intent-{suffix}",
            "workflow_key": "payments.standard",
            "action_type": "transfer",
            "amount_minor": 800000,
            "currency": "USD",
            "source_account_ref": "acct-source-501",
            "destination_account_ref": "acct-destination-501",
            "destination_country": "GB",
            "evidence_refs": [],
        },
        "evaluation_context": {"risk_tier": "low", "evidence_present": True},
        "client_tags": ["contract", "pccb"],
    }


def test_live_pccb_issuance_conforms_to_pinned_kernel_contract(
    client: TestClient,
    test_settings: Settings,
) -> None:
    tenant = create_tenant(client)
    create_allow_policy(client, tenant["tenant_id"])
    signing_key = create_signing_key(client, tenant["tenant_id"])

    intake_response = client.post(
        "/api/v1/action-intents",
        json=build_intake_payload(tenant["tenant_id"]),
    )
    assert intake_response.status_code == 201
    intake_body = intake_response.json()

    issuance_response = client.post(
        "/api/v1/issuance/proofs",
        json={
            "action_intent_record_id": intake_body["action_intent_record_id"],
            "proof_kind": "pccb",
            "audience": "finance-ops.internal",
            "scope": ["finance.transfer.release", "finance.transfer.audit"],
            "requested_by": {
                "principal_type": "user",
                "principal_id": "contract-issuer-001",
            },
            "signing_key_reference_id": signing_key["signing_key_reference_id"],
        },
    )

    assert issuance_response.status_code == 201
    issued_proof = issuance_response.json()
    assert issued_proof["status"] == "issued"
    assert (
        issued_proof["proof_payload"]["binding"]["contract_version_ref"]
        == "open_execution_kernel.action_intent.finance.v1alpha1"
    )

    verification_result = verify_pccb_artifact(
        issued_proof,
        secret=test_settings.dev_signing_secret,
    )
    assert verification_result.accepted, verification_result.errors


def test_known_good_pccb_fixture_round_trips_through_contract_verification() -> None:
    artifact = load_json_fixture(KNOWN_GOOD_PCCB_PATH)

    verification_result = verify_pccb_artifact(
        artifact,
        secret=DEFAULT_DEV_SIGNING_SECRET,
    )

    assert verification_result.accepted, verification_result.errors


def test_mutated_kernel_action_intent_contract_is_refused_structurally_not_500(
    client: TestClient,
) -> None:
    tenant = create_tenant(client)
    create_allow_policy(client, tenant["tenant_id"])

    mutated_payload = copy.deepcopy(build_intake_payload(tenant["tenant_id"], suffix="002"))
    del mutated_payload["kernel_action_intent"]["destination_account_ref"]

    response = client.post("/api/v1/action-intents", json=mutated_payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["contract_validation_status"] == "invalid"
    assert body["decision_state"] == "structurally_non_executable"
    assert (
        body["decision_reason"] == "external Action Intent failed versioned contract validation"
    )
    assert any(
        "destination_account_ref" in error and "required property" in error
        for error in body["contract_validation_errors"]
    )
    assert body["evaluation_trace"][0]["reason"] == "contract_validation_failed"
