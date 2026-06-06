# Logging Collection

## Purpose

This document defines the minimum logging model for a managed single-tenant invoice payment pilot.

## Application Logging

The Actenon Cloud application already emits structured logs and should continue writing them to standard output and standard error.

Current log output is intended to be collected by the hosting environment and forwarded to a central log destination.

## Reverse Proxy Logging

If NGINX is used, the example configuration in `deploy/nginx/action-control-plane.conf` writes:

- access logs to `/dev/stdout`
- error logs to `/dev/stderr`

This keeps app and ingress logs compatible with container-native log collection.

## Central Collection Model

Use one central log destination per pilot environment, such as:

- a managed log service
- a host-level log forwarder
- a container-platform log sink

This repo does not require a specific vendor.

## Minimum Requirements

- app logs are retained centrally
- reverse proxy logs are retained centrally
- logs are segmented by pilot environment
- operators can search for request failures, startup failures, and readiness failures

## Useful Fields

The application log stream should preserve fields such as:

- event name
- request identifier
- log level
- startup phase
- dependency check name and status
- error class and message

## What Is Still Manual

- this repo does not ship a log forwarder
- alerting on top of the central log sink is still an operator responsibility
- metrics and tracing are still out of scope for this minimum pilot-hosting pass
