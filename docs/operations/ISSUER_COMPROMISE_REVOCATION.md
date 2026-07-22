# Issuer Compromise Revocation Runbook

## Objective

Revoke a compromised issuer, publish a signed revoked status artifact, and
notify relying parties within the configured maximum staleness window.

Default maximum staleness: **300 seconds from artifact issuance**.

## Trigger Conditions

Start this runbook when any of these is credible:

- issuer signing material may be compromised
- issuer approval authority is no longer trustworthy
- issuer identity control is lost
- an issuer requests emergency revocation
- monitoring detects unauthorized proof issuance

## Immediate Containment

1. Open an incident record and assign an incident commander.
2. Record the issuer type, issuer ID, detection time, and evidence reference.
3. Disable proof issuance for the issuer at every reachable issuance path.
4. Block new standing changes except actions needed for revocation.
5. Preserve audit logs and provider operation references.

Do not wait for status signing to become healthy before committing the
registry revocation.

## Revoke And Publish

1. Authenticate as an authorized platform administrator.
2. Call:

   ```text
   POST /api/v1/issuer-registry/issuers/{registry_id}/revoke
   ```

3. Supply a concise incident-backed reason.
4. Confirm the registry record is `revoked` and its status version increased.
5. Confirm the response contains a P12 artifact with:
   - `status: revoked`
   - the expected issuer identity
   - the expected authority
   - the active public `kid`
   - expiry no later than the maximum staleness window
6. Fetch the public status endpoint without operator credentials.
7. Verify the artifact offline with the open P12 verifier and published keys.
8. Confirm the verifier returns `ISSUER_REVOKED`.

## Signing Or Publication Outage

If publication fails:

1. Confirm durable registry state is still `revoked`.
2. Confirm the public status endpoint does not serve the older status version.
3. Treat `503` as the expected fail-closed result while recovery proceeds.
4. Restore the managed HSM/KMS signing path under the P10 recovery controls.
5. Re-run explicit status publication for the revoked issuer.
6. Verify the new artifact offline.

Do not restore the issuer to good standing to work around a signing outage.

## Relying-Party Notification

Notify relying parties immediately with:

- issuer type and issuer ID
- revocation effective time
- current status endpoint
- published public key-set location
- configured maximum staleness
- incident contact channel

State clearly that a previously cached good-standing artifact may remain
cryptographically valid until its short expiry. Ask high-assurance relying
parties to refresh immediately and continue to fail closed on missing or
unverifiable status.

## Monitoring And Escalation

Alert on:

- `issuer.revoked` audit events
- failed status publication
- requested publications that do not complete
- public endpoint unavailability
- HSM/KMS signing errors
- clock skew approaching the status validity tolerance

Escalate if a revoked artifact is not independently verifiable within the
configured maximum staleness window.

## Closure Checklist

- [ ] issuer is durably marked `revoked`
- [ ] proof issuance is disabled for the issuer
- [ ] current revoked artifact is publicly retrievable
- [ ] public P12 verifier returns `ISSUER_REVOKED`
- [ ] artifact expiry is within the configured maximum staleness
- [ ] registry and signing audit records are preserved
- [ ] relying parties were notified
- [ ] root cause and corrective actions are documented
- [ ] runbook timing was compared with the freshness objective

