# ADR-006: Browser-Local Run History

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

The server already retains run metadata for one hour but has no identity boundary.
A server-wide history endpoint would let anonymous callers enumerate other users'
model inputs and run IDs. Durable or private history would require metadata storage,
retention policy, ownership, and authorization that the baseline explicitly excludes.

## Decision Drivers

- Let a user return to recent runs without enabling global enumeration.
- Reuse existing opaque run IDs and status lifecycle.
- Make one-hour expiry and restart loss honest.
- Bound retained browser data and handle malformed data safely.
- Avoid claiming cross-device, private, or durable history.

## Options Considered

### Option A: Capped Browser-Local Index of Opaque Run IDs

- **Benefits:** No server list endpoint or database; naturally scoped to one browser
  profile; can revalidate against the existing status endpoint.
- **Costs:** Lost when site data is cleared or another browser/device is used; anyone
  sharing the profile can see stored summaries.
- **Failure modes:** Corrupt storage, expired IDs, quota errors, or stale summaries.
- **Reversibility:** High; it is client-side convenience state.

### Option B: Anonymous Server-Wide History

- **Benefits:** Simple server list and visibility across browsers.
- **Costs:** Exposes unrelated run identifiers and model inputs without ownership.
- **Failure modes:** Privacy leakage and unbounded or confusing shared history.
- **Reversibility:** Public enumeration behavior is difficult to retract cleanly.

### Option C: Durable Per-User History

- **Benefits:** Private cross-device access, longer retention, deletion, and audit.
- **Costs:** Requires identity, authorization, durable metadata/artifacts, migrations,
  retention/deletion policy, and tenant-isolation testing.
- **Failure modes:** Authorization bypass, data leakage, and inconsistent deletion.
- **Reversibility:** Low because ownership and retention become product contracts.

## Recommendation

Choose Option A. Store at most 20 entries containing the opaque run ID, submission
time, and a minimal request summary in `localStorage`. Treat all stored data as
untrusted and render through DOM text properties. On page load, validate IDs, fetch
the existing status endpoint, update valid entries, and prune malformed, unknown, or
expired entries. Selecting a valid entry restores status/results without submitting
new work. Provide a browser-only clear-history action and document all loss/privacy
limitations.

## Consequences

- **Positive:** Useful refresh/browser-revisit behavior without exposing a server
  enumeration endpoint.
- **Positive:** No new backend persistence or identity dependency.
- **Negative:** History is not cross-device, durable, private from a shared browser
  profile, or guaranteed past server TTL/restart.
- **Negative:** Client storage failure needs graceful degradation.

## Validation

1. Test cap, ordering, duplicate update, malformed JSON, invalid IDs, expiry pruning,
   storage exceptions, and clear action.
2. Use Playwright MCP for refresh restore, expired pruning, clear history, narrow
   viewport, keyboard use, two browser contexts with separate local history, and
   same-profile tabs submitting concurrently.
3. Verify no unsafe HTML insertion and no new server list-runs endpoint.

## What Would Change This Decision

- History must be private, durable, cross-device, searchable, or exportable.
- Retention must exceed the run TTL or survive pod replacement.
- Users need deletion guarantees, audit, ownership, or sharing.

## Links

- Related task: TASK-010 in `TASKS.md`
- Related decision: ADR-002
