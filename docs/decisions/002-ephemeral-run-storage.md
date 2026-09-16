# ADR-002: Ephemeral Run and Artifact Storage

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

Each AIConfigurator run produces structured result data plus a directory of YAML,
configuration, script, CSV, and image artifacts. The portal must serve results and a
download, but the assignment explicitly does not require production hardening,
multi-user history, or high availability. The storage choice determines restart,
cleanup, URL, rollout, and security behavior.

## Decision Drivers

- Complete the run-to-download path within the take-home time budget.
- Keep files scoped to opaque server-generated run IDs.
- Define retention and cleanup rather than allowing unbounded disk use.
- Make data-loss behavior explicit and testable.
- Preserve a migration path when durable history becomes a requirement.

## Options Considered

### Option A: Pod-Local `emptyDir` and In-Memory Metadata

- **Benefits:** No external service, credential, schema, or local-cluster provisioner;
  artifact writes are fast and use the layout AIConfigurator already generates.
- **Costs:** Metadata is bound to one process; artifacts disappear with pod deletion;
  container restart leaves files without metadata unless startup cleans them.
- **Failure modes:** Active and completed runs become unavailable on process/pod
  replacement; disk pressure can evict the pod if capacity is not bounded.
- **Security:** Run directories use server-generated UUIDs beneath one fixed root;
  downloads are assembled from that root without accepting a user-supplied path.
- **Reversibility:** A storage interface can later target object storage and a
  metadata database.

### Option B: Persistent Volume Plus Local Metadata Database

- **Benefits:** Results can survive container and pod replacement on one deployment.
- **Costs:** Needs a storage class, schema/migrations, recovery/reconciliation, and a
  single-writer assumption or shared-filesystem semantics.
- **Failure modes:** Volume attachment and orphan metadata/files; not enough by
  itself for multiple replicas.
- **Reversibility:** Moderate; file URLs and cleanup logic still need redesign for
  object storage at scale.

### Option C: Object Storage Plus Durable Database

- **Benefits:** Durable artifacts, lifecycle policies, scalable downloads, and clean
  separation between metadata and blobs.
- **Costs:** Two external systems, credentials, local emulation, retries, and cleanup
  consistency are disproportionate to the must-have demo.
- **Failure modes:** Partial writes across systems, expired links, permission and
  network errors.
- **Reversibility:** Best long-term storage model, highest initial cost.

## Recommendation

Choose Option A for this assignment. Keep run metadata in memory and all files under
`/var/lib/portal/runs/{run_id}` on a size-limited Kubernetes `emptyDir`. Retain a
terminal run for one hour, then remove its metadata and directory through a periodic
cleanup task. Clean orphaned run directories during startup. The result endpoint
returns `404` after restart or expiry; README and UI state this plainly.

The download endpoint is available only for completed runs and streams a ZIP created
from the specific run root. It returns `409` while incomplete and `404` for unknown
or expired runs. It does not accept artifact paths. Artifact contents and generated
manifests are never logged or automatically applied.

## Consequences

- **Positive:** The must-have download is demonstrable without introducing an
  unrelated database/storage stack.
- **Positive:** Cleanup and storage capacity are explicit.
- **Negative:** Bookmarked URLs and completed results do not survive pod replacement;
  this is a conscious take-home limitation.
- **Negative:** Rolling updates cannot preserve jobs, reinforcing ADR-001's one
  replica and `Recreate` rollout.
- **Follow-up:** Add a metadata repository and artifact-store interface before
  implementing history, caching, multi-user access, or multiple replicas.

## Validation

- Verify successful ZIP content belongs only to the requested run.
- Verify queued/running, failed, unknown, malformed, and expired run downloads fail
  with the documented status.
- Use a short test TTL to prove metadata and directories are deleted.
- Restart the application and verify orphan cleanup plus documented `404` behavior.
- Fill or constrain temporary storage in a test and verify the run fails clearly
  without making probes unhealthy.

## What Would Change This Decision

- Results must survive pod replacement, remain bookmarkable beyond one hour, or be
  shared across replicas.
- Run history, caching, audit, cancellation, or user/team ownership is required.
- Artifact size or request volume makes pod-local disk or application-streamed ZIPs
  operationally unsafe.

## Links

- Related requirements: `docs/project-brief.md`
- Related tasks: TASK-003, TASK-005, and TASK-006 in `TASKS.md`
- Related decision: ADR-001
