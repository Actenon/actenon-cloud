# Deployment And Operations Index

## Purpose

This is the quick index for deploying and operating the managed single-tenant invoice payment pilot.

Use this document when you need to answer:

- how is the pilot deployed
- what infrastructure is required
- what does the provider operate
- what does the customer operate
- how is the pilot verified after release
- where do usage, reporting, and operating truth live

## Fast Answers

### What Is The Deployment Shape

- one app runtime
- one migration step from the same image
- one managed PostgreSQL database
- one mounted persistent evidence path
- one TLS ingress or reverse proxy
- one central log collection path

### What Is Provider-Operated

- deployment and release execution
- database, storage, TLS, logs, and secrets
- early auth bootstrap
- hosted-environment incident triage
- pilot support and runtime troubleshooting

### What Is Customer-Operated

- held-action review
- approval and evidence handling
- receipt and trace review
- business interpretation of allowed, held, and refused outcomes

### What Is Still Outside This Repo

- proof verification, through a separate verifier repo or verifier interface
- downstream payment execution itself
- billing and invoicing workflows

## Recommended Reading Order

### 1. Understand The Live System

- [LIVE_PILOT_OVERVIEW.md](LIVE_PILOT_OVERVIEW.md)
- [README.md](README.md)
- [docs/OPEN_KERNEL_DEPENDENCY_MODEL.md](docs/OPEN_KERNEL_DEPENDENCY_MODEL.md)

### 2. Understand Hosted Deployment Truth

- [HOSTING_AND_DEPLOYMENT_STATUS.md](HOSTING_AND_DEPLOYMENT_STATUS.md)
- [HOSTED_PILOT_RUNTIME.md](HOSTED_PILOT_RUNTIME.md)
- [HOSTED_PILOT_TOPOLOGY.md](HOSTED_PILOT_TOPOLOGY.md)
- [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md)

### 3. Use The Concrete Deployment Artifacts

- [docs/CONTAINERIZED_DEPLOYMENT.md](docs/CONTAINERIZED_DEPLOYMENT.md)
- [deploy/env/hosted-pilot.env.example](deploy/env/hosted-pilot.env.example)
- [deploy/nginx/action-control-plane.conf](deploy/nginx/action-control-plane.conf)

### 4. Verify A Deployment

- [HOSTED_PILOT_VERIFICATION_CHECKLIST.md](HOSTED_PILOT_VERIFICATION_CHECKLIST.md)
- [DEPLOYMENT_VERIFICATION.md](DEPLOYMENT_VERIFICATION.md)
- [PILOT_GO_LIVE_CHECKLIST.md](PILOT_GO_LIVE_CHECKLIST.md)

### 5. Run The Pilot Week To Week

- [CUSTOMER_HANDOFF_GUIDE.md](CUSTOMER_HANDOFF_GUIDE.md)
- [CUSTOMER_OPERATING_MODEL.md](CUSTOMER_OPERATING_MODEL.md)
- [PILOT_ROLES_AND_RESPONSIBILITIES.md](PILOT_ROLES_AND_RESPONSIBILITIES.md)
- [PILOT_SUPPORT_MODEL.md](PILOT_SUPPORT_MODEL.md)
- [PILOT_REPORTING_CADENCE.md](PILOT_REPORTING_CADENCE.md)
- [USAGE_METERING.md](USAGE_METERING.md)

### 6. Handle Exceptions And Incidents

- [EXCEPTION_HANDLING_RUNBOOK.md](EXCEPTION_HANDLING_RUNBOOK.md)
- [CUSTOMER_INCIDENT_FLOW.md](CUSTOMER_INCIDENT_FLOW.md)
- [INCIDENT_TRIAGE_RUNBOOK.md](INCIDENT_TRIAGE_RUNBOOK.md)
- [INTERNAL_OBSERVABILITY.md](INTERNAL_OBSERVABILITY.md)
- [docs/TRANSPARENCY_LOG_SERVICE.md](docs/TRANSPARENCY_LOG_SERVICE.md)
- [docs/operations/TRANSPARENCY_LOG_INTEGRITY_RUNBOOK.md](docs/operations/TRANSPARENCY_LOG_INTEGRITY_RUNBOOK.md)
- [docs/ISSUER_REGISTRY_SERVICE.md](docs/ISSUER_REGISTRY_SERVICE.md)
- [docs/operations/ISSUER_COMPROMISE_REVOCATION.md](docs/operations/ISSUER_COMPROMISE_REVOCATION.md)

## Minimum Design-Partner Deployment Pack

If a design partner only needs the most important deployment and operations docs, use this set:

1. [README.md](README.md)
2. [LIVE_PILOT_OVERVIEW.md](LIVE_PILOT_OVERVIEW.md)
3. [CUSTOMER_HANDOFF_GUIDE.md](CUSTOMER_HANDOFF_GUIDE.md)
4. [HOSTING_AND_DEPLOYMENT_STATUS.md](HOSTING_AND_DEPLOYMENT_STATUS.md)
5. [docs/CONTAINERIZED_DEPLOYMENT.md](docs/CONTAINERIZED_DEPLOYMENT.md)
6. [HOSTED_PILOT_VERIFICATION_CHECKLIST.md](HOSTED_PILOT_VERIFICATION_CHECKLIST.md)
7. [USAGE_METERING.md](USAGE_METERING.md)

## Important Current Truth

This index is for a managed pilot, not a broad hosted-product claim.

The current repo supports:

- a repeatable pilot deployment form
- a supervised operator workflow for one invoice payment path
- usage and trace reporting for that workflow

It does not yet claim:

- self-serve onboarding
- broad multi-tenant hosted delivery
- finished production auth, signing, storage, or observability
- a billing platform
