# ADR-007: Anonymous Multi-User Capacity Awareness

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

The single-pod portal admits one active and four queued runs, but browser users see
shared pressure only after submitting and possibly receiving `429`. The request asks
for multi-user awareness "of any kind," not authentication or tenant isolation. The
smallest useful signal is anonymous aggregate capacity, not identity-like sessions.

## Decision Drivers

- Explain current shared queue pressure before submission.
- Reveal no run IDs, model inputs, timestamps, IP addresses, or user identifiers.
- Remain low-cardinality, responsive, and bounded during CPU work.
- Avoid implying accounts, ownership, authorization, or quotas.
- Preserve the accepted one-process capacity model.

## Options Considered

### Option A: Anonymous Aggregate Capacity Endpoint and Banner

- **Benefits:** Directly useful; reuses run-manager counters; exposes no identities or
  run details; simple to test and remove.
- **Costs:** Counts are approximate by the time they render and do not reserve a slot.
- **Failure modes:** Excess polling or confusing stale capacity.
- **Reversibility:** High; additive read-only endpoint and UI.

### Option B: Anonymous Session Ownership

- **Benefits:** Could separate browser-visible runs and enable per-session history.
- **Costs:** Signed cookies, ownership semantics, rotation, shared-browser behavior,
  and false expectations of security without authentication.
- **Failure modes:** Session loss, fixation, accidental data exposure, or quota abuse.
- **Reversibility:** Moderate because session ownership affects every run endpoint.

### Option C: Authenticated Users with Ownership and Quotas

- **Benefits:** Defensible isolation, private history, quotas, and audit.
- **Costs:** Identity provider, authorization policy, durable admission state,
  credentials, and extensive security testing.
- **Failure modes:** Authentication outage, authorization bypass, and tenant leakage.
- **Reversibility:** Low because identity becomes a public system boundary.

## Recommendation

Choose Option A. Add a read-only endpoint containing only active count, queued count,
configured active/queue capacity, and whether admission is open. Show a neutral UI
banner such as "1 run active; 2 waiting" and explicitly state that the portal has no
accounts or private ownership. Poll no more frequently than the existing status
interval and only while the page is visible. The response is informational and does
not reserve capacity.

## Consequences

- **Positive:** Users can see shared load without submitting or exposing one another.
- **Positive:** No cookies, identity dependency, or high-cardinality telemetry.
- **Negative:** This is awareness only, not fairness, reservation, ownership, or
  protection from queue races.
- **Negative:** Polling adds a small amount of read traffic.

## Validation

1. Test idle, active, queued, saturated, and shutting-down payloads.
2. Verify the endpoint exposes only allowlisted aggregate fields and stays responsive
   during a real sweep.
3. Use Playwright MCP with two browser contexts to confirm shared counts, visibility
   polling behavior, narrow layout, keyboard access, and honest no-account wording.

## What Would Change This Decision

- Users require private ownership, per-user quotas, fairness, reservations, or audit.
- Multiple replicas require shared admission state.
- Capacity polling causes measurable load or stale-state confusion.

## Links

- Related task: TASK-011 in `TASKS.md`
- Related decision: ADR-001
