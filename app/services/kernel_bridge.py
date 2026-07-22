"""Actenon-Cloud ↔ Actenon-Kernel bridge.

This module is the concrete implementation of the ``export_kernel_pccb``
adapter that the cross-repo wire contract anticipated. It replaces cloud's
previous pattern of building a parallel ``IssuedProof`` and signing with
dev-HMAC — now cloud builds a REAL kernel PCCB via ``PCCBMinter.mint`` and
signs with the kernel's canonicalization.

This is the single translation layer between cloud's domain (tenants,
actors, invoices, approval workflows) and the kernel's domain
(ActionIntent, PolicyDecision, DynamicContextInput, PCCB).

See ARCHITECTURE.md §3 for the "one artifact spine" decision this implements.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from actenon.models.contracts import (
    PCCB,
    ActionIntent,
    ActionSpec,
    AudienceRef,
    PartyRef,
    TargetRef,
    TenantRef,
)
from actenon.models.runtime import DynamicContextInput, PolicyDecision, RuleEvaluation
from actenon.proof.canonical import canonicalize_bytes, sha256_hex
from actenon.proof.service import PCCBMinter, PCCBVerifier, build_action_hash_input

# Re-export resolve_signer at module level so callers (e.g. escrow's broker
# release path) can import it from this bridge module. The function itself
# prefers Ed25519 (asymmetric) over dev-HMAC and is the canonical way to
# resolve a signer for any signed artifact minted by cloud.
from app.services.ed25519_signer import resolve_signer  # noqa: E402,F401


class CloudKernelBridgeError(RuntimeError):
    """Raised when the bridge cannot translate or verify."""


def _canonicalize_value(v: Any) -> Any:
    """Convert a value to a kernel-canonicalizable form.

    The kernel's actenon-jcs-sha256-v1 canonicalization rejects floats.
    Cloud uses floats for amounts in some paths. We stringify floats with
    repr() for deterministic hashing.
    """
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, dict):
        return {k: _canonicalize_value(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_canonicalize_value(item) for item in v]
    return v


def _canonicalize_params(params: dict[str, Any]) -> dict[str, Any]:
    return {k: _canonicalize_value(v) for k, v in params.items()}


def export_kernel_pccb(
    *,
    tenant_id: str,
    actor_id: str,
    action_name: str,
    action_capability: str,
    action_parameters: dict[str, Any],
    target_resource_type: str,
    target_resource_id: str,
    expires_at: datetime,
    issuer_id: str = "actenon-cloud",
    audience_id: str = "actenon-cloud-gateway",
    signing_secret: bytes | str | None = None,
    scope_capabilities: tuple[str, ...] | None = None,
):
    """Build and sign a real kernel PCCB for a cloud-governed action.

    This is the function the wire contract anticipated. It replaces cloud's
    previous IssuedProof-as-dict pattern with a real kernel PCCB built via
    PCCBMinter.mint.

    Returns (intent, pccb) where intent is needed later for edge verification
    and pccb is the signed kernel PCCB.
    """

    now = datetime.now(UTC)
    if expires_at < now:
        raise CloudKernelBridgeError(f"expires_at {expires_at} is in the past")

    parameters = _canonicalize_params(dict(action_parameters))
    intent = ActionIntent(
        intent_id=f"intent_{uuid4().hex[:16]}",
        issued_at=now,
        expires_at=expires_at,
        tenant=TenantRef(tenant_id=tenant_id),
        requester=PartyRef(type="actor", id=actor_id),
        action=ActionSpec(
            name=action_name,
            capability=action_capability,
            parameters=parameters,
        ),
        target=TargetRef(resource_type=target_resource_type, resource_id=target_resource_id),
    )

    decision = PolicyDecision(
        outcome="allow",
        summary=f"cloud policy allowed {action_name}",
        rule_evaluations=(
            RuleEvaluation(
                rule_id="cloud-policy-engine",
                outcome="allow",
                reason_code="CLOUD_POLICY_ALLOW",
                summary=f"{action_name} approved by cloud policy",
            ),
        ),
    )

    context = DynamicContextInput(
        request_id=f"req_{uuid4().hex[:8]}",
        audience=AudienceRef(type="service", id=audience_id),
        scope_capabilities=scope_capabilities or (action_capability,),
        now=now,
        max_ttl_seconds=int((expires_at - now).total_seconds()) or 900,
    )

    # Phase 4: prefer Ed25519 (asymmetric) over HMAC.
    from app.services.ed25519_signer import resolve_signer

    signer = resolve_signer(hmac_secret=signing_secret)

    minter = PCCBMinter(
        signer=signer,
        issuer=PartyRef(type="service", id=issuer_id),
    )
    pccb = minter.mint(intent, decision, context)
    return intent, pccb


def verify_kernel_pccb_at_edge(
    intent,
    pccb,
    *,
    tenant_id: str,
    actor_id: str,
    action_name: str,
    action_capability: str,
    action_parameters: dict[str, Any],
    target_resource_type: str,
    target_resource_id: str,
    expires_at: datetime,
    audience_id: str = "actenon-cloud-gateway",
    signing_secret: bytes | str | None = None,
    scope_capabilities: tuple[str, ...] | None = None,
) -> None:
    """Verify a kernel PCCB at the cloud execution edge.

    Raises ProofVerificationError if the proof is invalid for ANY reason.
    Builds a FRESH intent from the actual action parameters — if any
    parameter was mutated between issuance and execution, the kernel rejects
    it (ACTION_MISMATCH, TARGET_MISMATCH, or ACTION_HASH_MISMATCH).
    """

    # Phase 4: prefer Ed25519 (asymmetric) over HMAC.
    from app.services.ed25519_signer import resolve_signer

    signer = resolve_signer(hmac_secret=signing_secret)
    verifier = PCCBVerifier(signer=signer)

    now = datetime.now(UTC)
    context = DynamicContextInput(
        request_id=f"req_{uuid4().hex[:8]}",
        audience=AudienceRef(type="service", id=audience_id),
        scope_capabilities=scope_capabilities or (action_capability,),
        now=now,
    )

    parameters = _canonicalize_params(dict(action_parameters))
    actual_intent = ActionIntent(
        intent_id=intent.intent_id,
        issued_at=intent.issued_at,
        expires_at=intent.expires_at,
        tenant=intent.tenant,
        requester=intent.requester,
        action=ActionSpec(
            name=action_name,
            capability=action_capability,
            parameters=parameters,
        ),
        target=TargetRef(resource_type=target_resource_type, resource_id=target_resource_id),
    )
    verifier.verify(actual_intent, pccb, context)


def pccb_action_hash(pccb) -> str:
    """Return the action-hash from a PCCB (for ledger dedup)."""
    return pccb.action_hash.value


def pccb_to_dict(pccb) -> dict[str, Any]:
    """Serialize a kernel PCCB to a dict for storage/transit."""
    return pccb.to_dict()


def pccb_from_dict(data: dict[str, Any]):
    """Deserialize a kernel PCCB from a dict."""
    return PCCB.from_dict(data)


__all__ = [
    "CloudKernelBridgeError",
    "export_kernel_pccb",
    "verify_kernel_pccb_at_edge",
    "pccb_action_hash",
    "pccb_to_dict",
    "pccb_from_dict",
    "build_action_hash_input",
    "canonicalize_bytes",
    "sha256_hex",
    "resolve_signer",
]
