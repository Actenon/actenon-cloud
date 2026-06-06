# TLS Setup

## Purpose

This document defines the minimum TLS model for a managed single-tenant invoice payment pilot deployment.

## Minimum TLS Shape

- one pilot-specific hostname
- TLS termination at the ingress or reverse proxy
- plain HTTP only on the private hop between the reverse proxy and the app runtime
- no certificate material baked into the application image

## Recommended Termination Point

Terminate TLS outside the Actenon Cloud process:

- at a managed load balancer, or
- at a reverse proxy such as NGINX

The application container should continue serving HTTP on its private port.

## Example Artifact

An example reverse-proxy configuration is provided in:

- `deploy/nginx/action-control-plane.conf`

It is a pilot example, not a production traffic-management standard.

## Certificate Handling

Use one of these two approaches:

1. Managed certificate support from the hosting layer.
2. Mounted certificate and key files on the reverse proxy host or container.

In both cases:

- keep private keys outside the application image
- restrict file access to the reverse proxy runtime
- rotate certificates through the hosting environment, not through application code

## Ingress Expectations

- `https://<pilot-hostname>` is the public entry point
- all `http://` traffic redirects to `https://`
- forwarded headers are preserved to the application
- TLS is required before pilot go-live

## Verification

Before go-live, confirm:

- the certificate matches the pilot hostname
- the TLS endpoint serves the application and pilot UI
- `/api/v1/health/live` and `/api/v1/health/ready` respond through the TLS endpoint

## Current Limits

- this repo does not automate certificate issuance
- this repo does not include a managed ingress controller
- TLS setup is still an operator-managed deployment step for the hosted pilot
