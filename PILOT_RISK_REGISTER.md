# Pilot Risk Register

## Purpose

This register captures the main risks for the invoice payment execution pilot.

## Risks

| Risk | Current Reality | Pilot Mitigation | Residual Risk |
| --- | --- | --- | --- |
| Capability release is simulated | The repo does not yet integrate a real protected-resource broker | Keep the pilot focused on governed release decisions and receipt traceability; require explicit acknowledgment of the simulation boundary | Medium |
| Operator auth is early | The current implementation does not provide enterprise SSO | Limit pilot users, use non-default secrets, and operate in a controlled environment | Medium |
| Signing is early | The current signing path is development-local unless separately upgraded | Treat proof issuance as pilot-governed control evidence, not production trust infrastructure | Medium |
| Receipt completeness depends on customer process | The repo needs the customer or kernel path to post receipts back | Agree receipt source and ownership before pilot start | Medium |
| Out-of-scope action creep | Partners may try to expand into refunds, batches, or payout flows | Lock the wedge to invoice payment execution only | Low |
| Observability is limited | Metrics, tracing, and alerting are not fully implemented | Use structured logs, health checks, and manual operating review | Medium |
| Kernel compatibility drift | The repo uses pinned local copies of kernel contracts | Freeze pilot on the current contract version and avoid mid-pilot contract churn | Low |
| Manual exception handling load | Some exception resolution will still be manual | Keep pilot volumes low and use named operator ownership | Medium |

## Risk Posture

The pilot is commercially credible if the partner accepts that this is a controlled, narrow governance pilot rather than a claim of finished production payment infrastructure.
