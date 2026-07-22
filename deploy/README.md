# Deployment Artifacts

This directory contains the minimum concrete artifacts for a managed single-tenant invoice payment pilot deployment.

It is intentionally narrow:

- one hosted pilot environment template
- one reverse-proxy example for TLS termination
- no Kubernetes manifests
- no broad cloud abstraction layer

Use these artifacts together with:

- `HOSTED_PILOT_TOPOLOGY.md`
- `SINGLE_TENANT_DEPLOYMENT_MODEL.md`
- `INFRASTRUCTURE_ASSUMPTIONS.md`
- `RELEASE_DEPLOY_RUNBOOK.md`
- `DEPLOYMENT_VERIFICATION.md`

## Contents

- `env/hosted-pilot.env.example`
- `nginx/action-control-plane.conf`

These artifacts support a managed pilot operated by the Actenon Cloud team. They do not describe a broad self-serve product deployment model.
