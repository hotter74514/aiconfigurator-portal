# ADR-005: Bounded Result Cache

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

An AIConfigurator sweep is CPU-heavy but deterministic only for a precise request and
dependency/profile/generator/normalization version set. The current single-process
portal retains completed runs for one hour and loses all state on restart. A cache
must preserve fresh opaque run IDs, downloadable artifacts, bounded resource use,
and explicit invalidation without implying durability.

## Decision Drivers

- Avoid repeated work for identical recent completed requests.
- Never return results generated under ambiguous or different versions.
- Preserve existing submission and polling behavior.
- Keep memory use and telemetry cardinality bounded.
- Avoid introducing persistence infrastructure for a nice-to-have.

## Options Considered

### Option A: Bounded Process-Local Completed-Bundle Cache

- **Benefits:** Fits ADR-001/002; no new service or credentials; fastest reversible
  path; can cache rows, visualization bytes, source metadata, and artifact ZIP.
- **Costs:** Lost on restart and not shared across replicas; duplicate in-flight work
  is not eliminated.
- **Failure modes:** Stale namespace, oversized bundles, or eviction bugs.
- **Reversibility:** High; cache is behind the run-manager boundary.

### Option B: SQLite Cache on a Persistent Volume

- **Benefits:** Survives process/pod replacement on one replica.
- **Costs:** Schema, migrations, file/database reconciliation, volume provisioning,
  backup/retention expectations, and full-disk behavior.
- **Failure modes:** Metadata/artifact divergence, locking, and stale durable entries.
- **Reversibility:** Moderate because stored schema and durability become observable.

### Option C: Shared Database and Object Storage Cache

- **Benefits:** Durable, shareable across replicas, and suitable for larger artifacts.
- **Costs:** Two external systems, credentials, retries, consistency, and operations.
- **Failure modes:** Partial writes, stale objects, permission errors, and outages.
- **Reversibility:** Low relative to the current take-home architecture.

## Recommendation

Choose Option A. Cache only successful immutable completed bundles. Hash a canonical
serialization of every request field plus explicit AIConfigurator, performance
profile, generator mapping, and portal normalization schema versions. Unknown
version input disables cache reads and writes.

Bound the cache by TTL, entry count, and total bytes with deterministic LRU eviction.
On a hit, create a new completed run record and fresh opaque run ID; keep `POST
/api/runs` at `202`, and let the first poll observe completion. Do not cache failures
or running work, and do not coalesce in-flight requests in this increment. Emit only
low-cardinality hit, miss, and eviction metrics.

## Consequences

- **Positive:** Repeat requests can avoid the CPU-heavy sweep without changing the
  public lifecycle contract.
- **Positive:** Version ambiguity fails safely as a miss.
- **Negative:** Cache warmth disappears on restart and differs per process.
- **Negative:** Completed bundle bytes consume measured, explicitly capped memory.

## Validation

1. Test canonicalization and every namespace component.
2. Prove identical completed requests execute the worker once but receive distinct
   run IDs and equivalent results, visualization bytes, and ZIP content.
3. Test misses, failures, in-flight duplicates, TTL, count/byte LRU eviction, run
   expiry independence, metrics, and restart loss.
4. Exercise one hit and one post-restart miss in the container.

## What Would Change This Decision

- Cache entries must survive restart or be shared across replicas.
- Artifacts exceed the measured memory budget.
- Duplicate concurrent traffic justifies single-flight coordination.
- Inputs or dependency versions cannot be determined reliably.

## Links

- Related task: TASK-009 in `TASKS.md`
- Related decisions: ADR-001 and ADR-002
