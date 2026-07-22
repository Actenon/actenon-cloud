# Operated Issuer Registry And Revocation Service

## Purpose

Actenon Cloud maintains issuer identity and current standing, then publishes
short-lived signed issuer-status artifacts in the open P12 format. Relying
parties verify those artifacts with the public Actenon SDK and the published
public key set. They do not need to trust this service's implementation.

The registry supports three standing values:

- `good_standing`
- `suspended`
- `revoked`

Revocation is terminal for an issuer identity. A replacement must use a new
issuer identity and complete registration separately.

## Freshness Guarantee

The default status artifact lifetime and maximum staleness are both 300
seconds. The service enforces:

```text
artifact TTL <= maximum staleness
```

No artifact issued by this service can remain valid beyond the configured
maximum staleness window. A relying party using the P12 public verifier with
the same or a stricter `max_age_seconds` therefore stops accepting a cached
good-standing assertion no later than that window after its issuance.

The service cannot retract a status artifact already cached by a relying
party. Short validity, verifier fail-closed behavior, and prompt publication
of a revoked artifact bound that exposure.

## State And Publication Ordering

Standing changes are committed before a new status artifact is signed.
Public reads only return a completed artifact whose `status_version` exactly
matches the current registry record.

This ordering is deliberate:

1. commit `suspended` or `revoked` to durable registry state
2. increment the issuer status version
3. request managed signing through the P10 custody service
4. persist the signed P12 artifact and publication audit record
5. serve only the artifact for the current status version

If signing or publication fails after step 1, the issuer remains revoked and
the public status endpoint returns unavailable. It does not fall back to an
older good-standing artifact.

## Managed Signing Boundary

`CounterSigningIssuerStatusSigner` delegates signing to the existing P10
managed HSM/KMS service. The Cloud process receives only:

- the public `kid`
- the Ed25519 signature
- the provider operation reference

Raw private key material never enters the registry service. The published
public key set advertises `issuer_status` as a permitted key use and retains
historical keys by `kid` for offline verification.

The runtime identity used for status signing must have only
`issuer_status.sign`. Registry operators do not receive signing authority.

## Administrative Controls

All registry mutations require platform administrator authorization at the
HTTP boundary and an explicit service permission internally:

- `issuer_registry.register`
- `issuer_registry.status.manage`
- `issuer_registry.revoke`
- `issuer_registry.status.publish`

Every registration, standing transition, successful publication, and failed
publication creates a durable audit event with the actor identity, reason,
status version, and non-secret operational details.

## API Surface

Administrative endpoints:

```text
POST /api/v1/issuer-registry/issuers
GET  /api/v1/issuer-registry/issuers
GET  /api/v1/issuer-registry/issuers/{registry_id}
POST /api/v1/issuer-registry/issuers/{registry_id}/suspend
POST /api/v1/issuer-registry/issuers/{registry_id}/reinstate
POST /api/v1/issuer-registry/issuers/{registry_id}/revoke
POST /api/v1/issuer-registry/issuers/{registry_id}/status
GET  /api/v1/issuer-registry/issuers/{registry_id}/audit
```

Public verifier endpoint:

```text
GET /api/v1/issuer-registry/status?issuer_type=...&issuer_id=...
```

The public endpoint does not require an operator token. It returns a current
signed artifact or fails closed with an unavailable/not-found response.

## Runtime Configuration

```text
ACTION_CONTROL_PLANE_ISSUER_STATUS_AUTHORITY_TYPE=service
ACTION_CONTROL_PLANE_ISSUER_STATUS_AUTHORITY_ID=actenon-issuer-registry
ACTION_CONTROL_PLANE_ISSUER_STATUS_AUTHORITY_DISPLAY_NAME=Actenon Issuer Registry
ACTION_CONTROL_PLANE_ISSUER_STATUS_TTL_SECONDS=300
ACTION_CONTROL_PLANE_ISSUER_STATUS_MAX_STALENESS_SECONDS=300
```

Production startup must install a managed `issuer_status_signer` on the
FastAPI application state, following the same explicit custody-injection
pattern used by transparency checkpoint signing. Missing signing custody
causes publication to fail closed.

## Verification

Relying parties use the public P12 verifier:

```python
from actenon.verifier import verify_issuer_status

verified = verify_issuer_status(
    issuer,
    status_artifact,
    published_public_keys,
    now,
    max_age_seconds=300,
)
```

The verifier rejects missing, expired, stale, unverifiable, suspended, and
revoked status artifacts. See the open
[`issuer_status` v1 specification](https://github.com/Actenon/actenon/blob/main/spec/issuer-status/SPEC.md).

## Operational Requirements

- monitor failed or stuck status publications
- alert on every suspension and revocation
- keep database time and HSM/KMS time synchronized
- publish public keys before activating a new signing `kid`
- retain historical public keys needed to verify unexpired artifacts
- rehearse the issuer-compromise runbook

See
[ISSUER_COMPROMISE_REVOCATION.md](operations/ISSUER_COMPROMISE_REVOCATION.md).

