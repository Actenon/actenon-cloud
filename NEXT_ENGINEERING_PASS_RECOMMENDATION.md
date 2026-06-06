# Next Engineering Pass Recommendation

## Recommended Next Pass

Production trust-boundary hardening.

## Why This Is The Highest-Value Next Step

The current repo already proves the core control-plane workflow:

- intake
- policy
- approvals
- evidence
- proof issuance
- escrow lifecycle
- receipts
- audit

The biggest remaining gap is not feature breadth. It is the trust boundary around operating the service in a real production setting.

## What The Next Pass Should Focus On

1. Replace development bearer auth with a production-grade operator identity model.
2. Replace ad hoc service tokens with production service-to-service identity.
3. Bind workflow actors more tightly to authenticated sessions on mutation paths.
4. Move signing from development-local HMAC to managed KMS or HSM-backed signing.
5. Replace simulated capability release with a real external managed release integration boundary.
6. Add production observability and deployment hardening basics.

## Why This Pass Should Come Before More Features

More feature breadth will increase system surface area, but it will not remove the main reasons the repo is still red for production deployment.

The current highest-value move is to make the existing flow trustworthy enough to operate, not to add more endpoints.

## Concrete Outcome Target

After the next pass, Actenon Cloud should be able to say:

- pilot and internal auth flows no longer depend on development-only bearer assumptions
- signing is backed by managed infrastructure
- service identity is explicit and auditable
- capability release is no longer only simulated
- the deployment posture is credible for controlled production rollout planning
