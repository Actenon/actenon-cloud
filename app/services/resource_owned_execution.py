"""Cloud-side resource-owned execution service (Prompt 9).

Cloud is the managed control plane. In ``brokered`` mode, it acts as
the broker (issuing proofs, verifying them, invoking the provider
through a Permit-side adapter). In ``resource_owned`` mode, it acts
as the *submitter* — it obtains a proof from its authority, submits
the request + proof to an independently-operated resource boundary,
and produces a ``ResourceOwnedExecutionResult`` based on what the
resource returns.

This service is the Cloud layer of the Prompt-9 formalisation. It:

  * Uses the Permit-side ``ResourceOwnedSubmissionClient`` (Prompt 9)
    to do the actual HTTP submission and receipt verification.
  * Adds Cloud-specific concerns: tenant_id, audit logging,
    transparency log integration, multi-tenant key registry.
  * Enforces Cloud policy: which tenants are allowed to use
    resource_owned mode, which resource endpoints are whitelisted.

The service is intentionally thin. The hard rules (forged receipts
forced to outcome_unknown, submission not implying execution) are
enforced by the Permit + Protocol layers; Cloud does not re-implement
them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from actenon.execution.mode_aware import (
    ModeAwareExecutionResult,
    ResourceReceiptVerifier,
    ResourceSigningKey,
)
from actenon_protocol.execution_results import (
    FinalityStatus,
    ResourceOwnedExecutionState,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ResourceOwnedExecutionError(RuntimeError):
    """Raised when the Cloud-side resource-owned execution path fails."""


class ResourceEndpointNotWhitelistedError(ResourceOwnedExecutionError):
    """Raised when a tenant tries to submit to a resource endpoint that
    is not on the tenant's whitelist."""


class TenantNotAuthorisedForResourceOwnedError(ResourceOwnedExecutionError):
    """Raised when a tenant is not authorised to use resource_owned mode."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ResourceEndpointConfig:
    """Configuration for a whitelisted resource endpoint."""

    resource_id: str
    endpoint_url: str
    signing_key_id: str
    signing_key_secret: bytes
    timeout_seconds: float = 30.0


@dataclass
class ResourceOwnedExecutionService:
    """Cloud-side service for resource-owned execution.

    Wraps the Permit-side ``ResourceOwnedSubmissionClient`` with
    Cloud-specific concerns: tenant authorisation, endpoint
    whitelisting, and per-resource receipt-verifier configuration.

    The service does NOT re-implement receipt verification — it
    delegates to the Kernel-side ``ResourceReceiptVerifier`` via the
    Permit client. The hard rules (forged receipt -> outcome_unknown,
    submission != execution) are enforced at the lower layers.
    """

    # tenant_id -> set of resource_ids the tenant is allowed to submit to
    tenant_resource_whitelist: dict[str, set[str]] = field(default_factory=dict)
    # resource_id -> ResourceEndpointConfig
    endpoints: dict[str, ResourceEndpointConfig] = field(default_factory=dict)
    # Permit-side submission client factory (injected for testability)
    # Signature: (endpoint, resource_id, verifier, timeout) -> client.submit
    client_factory: Any = None  # type: ignore[assignment]

    def register_endpoint(self, config: ResourceEndpointConfig) -> None:
        """Register a resource endpoint with its signing key."""
        self.endpoints[config.resource_id] = config

    def authorise_tenant(self, tenant_id: str, resource_ids: set[str]) -> None:
        """Authorise a tenant to submit to a set of resource endpoints."""
        self.tenant_resource_whitelist[tenant_id] = set(resource_ids)

    def build_verifier_for(self, resource_id: str) -> ResourceReceiptVerifier:
        """Build a ResourceReceiptVerifier with the resource's signing key."""
        config = self.endpoints.get(resource_id)
        if config is None:
            raise ResourceOwnedExecutionError(
                f"resource endpoint {resource_id!r} is not registered"
            )
        verifier = ResourceReceiptVerifier()
        verifier.register_key(
            ResourceSigningKey(
                resource_id=config.resource_id,
                key_id=config.signing_key_id,
                secret=config.signing_key_secret,
            )
        )
        return verifier

    def submit(
        self,
        *,
        tenant_id: str,
        resource_id: str,
        action: Any,
        proof: dict[str, Any],
        pccb_id: str | None = None,
        action_hash: str | None = None,
    ) -> ModeAwareExecutionResult:
        """Submit a request + proof to a resource boundary.

        Raises ``TenantNotAuthorisedForResourceOwnedError`` if the
        tenant is not authorised to use resource_owned mode.
        Raises ``ResourceEndpointNotWhitelistedError`` if the resource
        is not on the tenant's whitelist.

        Returns a ``ModeAwareExecutionResult`` with mode=resource_owned.
        The state and finality reflect the resource's response and the
        cryptographic verification of the resource receipt.
        """
        # 1. Tenant authorisation.
        allowed = self.tenant_resource_whitelist.get(tenant_id, set())
        if not allowed:
            raise TenantNotAuthorisedForResourceOwnedError(
                f"tenant {tenant_id!r} is not authorised to use resource_owned mode"
            )
        if resource_id not in allowed:
            raise ResourceEndpointNotWhitelistedError(
                f"tenant {tenant_id!r} is not authorised to submit to resource {resource_id!r}"
            )

        # 2. Endpoint lookup.
        config = self.endpoints.get(resource_id)
        if config is None:
            raise ResourceOwnedExecutionError(
                f"resource endpoint {resource_id!r} is not registered"
            )

        # 3. Build the verifier + client.
        verifier = self.build_verifier_for(resource_id)
        if self.client_factory is None:
            # Default: use the Permit-side ResourceOwnedSubmissionClient.
            from actenon_permit.execution_modes import ResourceOwnedSubmissionClient

            client = ResourceOwnedSubmissionClient(
                resource_endpoint=config.endpoint_url,
                resource_id=config.resource_id,
                receipt_verifier=verifier,
                timeout_seconds=config.timeout_seconds,
            )
            submit_fn = client.submit
        else:
            # Test injection.
            submit_fn = self.client_factory(
                config.endpoint_url,
                config.resource_id,
                verifier,
                config.timeout_seconds,
            )

        # 4. Submit. The submit function returns a ModeAwareExecutionResult.
        result = submit_fn(action, proof, pccb_id=pccb_id, action_hash=action_hash)

        # 5. Cloud-side audit log (no credential value; the proof_id is fine to log).
        logger.info(
            "resource_owned_execution_submitted",
            extra={
                "tenant_id": tenant_id,
                "resource_id": resource_id,
                "state": result.state,
                "finality": result.finality.value,
                "pccb_id": pccb_id,
            },
        )

        return result

    def is_final(self, result: ModeAwareExecutionResult) -> bool:
        """Cloud convenience: returns True iff the result is final."""
        return result.finality == FinalityStatus.FINAL

    def requires_reconciliation(self, result: ModeAwareExecutionResult) -> bool:
        """Cloud convenience: returns True iff the result is non-final
        and may need reconciliation.

        ``submitted``, ``accepted``, and ``outcome_unknown`` (in
        resource_owned mode) all require reconciliation. The Cloud
        reconciliation service polls the resource for updates.
        """
        if result.finality == FinalityStatus.FINAL:
            return False
        if result.mode != "resource_owned":
            return False
        return result.state in (
            ResourceOwnedExecutionState.SUBMITTED.value,
            ResourceOwnedExecutionState.ACCEPTED.value,
            ResourceOwnedExecutionState.OUTCOME_UNKNOWN.value,
        )


__all__ = [
    "ResourceEndpointConfig",
    "ResourceEndpointNotWhitelistedError",
    "ResourceOwnedExecutionError",
    "ResourceOwnedExecutionService",
    "TenantNotAuthorisedForResourceOwnedError",
]
