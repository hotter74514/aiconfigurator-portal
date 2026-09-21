# ADR-012: Remove Generic Kubernetes Network and Scheduling Guidance

## Status

**Accepted**

## Decision Owner

Repository owner.

## Context

The portal's topology comparison included generic Kubernetes network and
scheduling recommendations beside source-derived worker and TP values. The
recommendations were not generated from a verified cluster topology, runtime
contract, or deployment manifest. They could therefore be read as deployment
instructions even though the portal only produces planning estimates.

The repository owner requested that these recommendations be removed. Kubernetes
sizing derived from verified source fields remains useful: disaggregated worker
counts map to Pod replicas and TP maps to GPUs per worker Pod. Aggregated
parallelism still must not be converted into a Pod count.

## Decision Drivers

- Keep the result contract limited to source evidence and deterministic sizing.
- Avoid presenting generic network or scheduling text as an operational directive.
- Preserve disaggregated worker/TP sizing when the SDK supplies the fields.
- Keep the change reversible if a future runtime contract supplies verified data.

## Options Considered

### Option A: Keep the existing generic recommendations

- Benefits: More explanatory text in the comparison view.
- Costs: Recommendations are not tied to a cluster or serving runtime.
- Failure modes: Users may mistake planning copy for validated deployment policy.
- Reversibility: Easy, but the ambiguity remains.

### Option B: Remove network and scheduling guidance, retain source-derived sizing

- Benefits: Preserves useful worker/TP arithmetic while removing unsupported
  operational advice.
- Costs: Operators must consult runtime and cluster documentation separately.
- Failure modes: Sizing is still unavailable when source fields are absent.
- Reversibility: Good; verified guidance can be added under a future ADR.

### Option C: Remove all topology and Kubernetes sizing

- Benefits: Smallest visible contract.
- Costs: Discards verified disaggregated sizing that directly answers the
  deployment-shape question.
- Failure modes: Users may independently reconstruct the same arithmetic.
- Reversibility: Easy, but loses useful evidence.

## Recommendation

Choose Option B. Remove `network` and `scheduling` from the comparison payload,
UI, tests, and documentation. Keep mode-specific topology fields and the
worker/TP sizing block, with explicit unavailable states for missing source
values.

## Consequences

- Positive: The portal no longer implies generic network or scheduling policy.
- Positive: The API remains useful for source-faithful Pod/GPU sizing.
- Negative: Cluster placement and KV-cache transport decisions are outside this
  portal's result contract.
- Follow-up work: Reintroduce operational guidance only with verified runtime or
  cluster evidence and a new accepted ADR.

## Validation

1. Normalize SDK `(p)workers`/`(d)workers` columns to the portal's canonical
   `(p)worker`/`(d)worker` fields.
2. Verify real completed-run API output exposes worker values and calculates
   disaggregated sizing from them.
3. Verify `network` and `scheduling` are absent from the API payload and UI.
4. Run configured checks, container build, Minikube rollout, and API smoke test.

## What Would Change This Decision

- AIConfigurator publishes a documented network or scheduling contract tied to
  the returned topology fields.
- The portal receives verified cluster topology data or deployment manifests.
- Product requirements explicitly request operational guidance with evidence.

## Links

- Related decision: [ADR-011](011-mode-aware-topology-semantics.md).
- Supersedes the network and scheduling guidance portion of ADR-011.
- Related task: TASK-021.
