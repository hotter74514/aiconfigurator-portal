# ADR-010: Rank-One Topology Fields and Kubernetes Guidance

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

The portal currently compares independently selected rank-one `agg` and
`disagg` rows for throughput, TTFT, TPOT, and total GPUs. The AIConfigurator
result may also contain the topology fields `(p)worker`, `(d)worker`, `(p)tp`,
and `(d)tp`. These fields are the evidence needed to explain a Kubernetes
deployment shape: worker counts describe the number of worker processes/pods,
while TP describes the GPU width required by each worker.

The UI must show those values in the existing "Aggregated vs disaggregated"
rank-one table and explain the resulting Kubernetes network and scheduling
constraints. It must not invent values when a source row omits a field, and it
must not turn an estimate into a production deployment guarantee.

This changes the completed-run comparison response and adds derived guidance
that downstream clients may consume, so the boundary should be explicit before
implementation.

## Decision Drivers

- Preserve the independently ranked rank-one semantics already accepted in
  ADR-004.
- Keep raw SDK field names available while presenting understandable labels.
- Derive pod counts from worker counts and GPU width from TP; never use TP as a
  replica count.
- Preserve missing or non-numeric values as unavailable rather than guessing.
- Give actionable network and scheduling guidance without applying manifests or
  claiming benchmark or cluster validation.
- Keep the additive change easy to test and easy to remove or version later.

## Options Considered

### Option A: Add topology metrics to the existing comparison metric list

- Benefits: Small API and browser change; one table contains all rank-one values
  and deltas.
- Costs: The table becomes wider; topology fields that are mode-specific need
  careful unavailable handling.
- Failure modes: Consumers may mistake worker/TP values for throughput metrics;
  a browser-only label mapping could drift from the API.
- Reversibility: Good; additive metric entries can be removed or versioned.

### Option B: Add a separate rank-one topology block and guidance payload

- Benefits: Separates performance metrics from deployment topology; the server
  can own worker-to-pod and TP-to-GPU semantics and emit structured guidance.
- Costs: Adds a second table or panel and a larger response shape.
- Failure modes: Duplicate display logic can make the comparison harder to scan;
  guidance can be stale if the deployment model changes.
- Reversibility: Good; the additive block can be removed without changing raw
  result rows.

### Option C: Derive topology and Kubernetes guidance only in the browser

- Benefits: No backend contract change.
- Costs: Domain semantics move into JavaScript, are harder to reuse and test,
  and can differ between clients.
- Failure modes: Wrong rank-one selection, incorrect replica calculation, or
  accidental use of TP as a pod count.
- Reversibility: Easy to edit, but weakens the ownership boundary.

## Recommendation

Choose Option B. Preserve the existing performance comparison table and add an
additive rank-one topology block containing the raw `(p)worker`, `(d)worker`,
`(p)tp`, and `(d)tp` values for each mode, plus structured Kubernetes guidance.
The guidance should state that worker counts determine prefill/decode pod
replicas, TP determines GPUs per worker/pod, and the topology fields are only
converted into counts when all required values are numeric. It should also
recommend keeping TP workers together on GPU-topology-compatible nodes,
prioritizing low-latency KV-cache transport, and using explicit Kubernetes
affinity/topology constraints rather than assuming all pods belong on one node.

The repository owner approved this recommendation. Implementation may proceed
within the scope and validation gates below.

## Consequences

- Positive: The portal answers the deployment-sizing question from the actual
  rank-one result instead of inferring pod count from TP or total GPUs.
- Positive: Missing topology fields remain honest and testable.
- Positive: Network and scheduling advice is visible beside the evidence that
  motivated it.
- Negative: The completed-run response gains an additive topology/guidance
  contract and the UI gains another responsive table/panel.
- Follow-up work: Add fixtures containing the four fields for both modes, test
  the pod/GPU arithmetic and missing-value behavior, and verify desktop, narrow,
  and keyboard browser states.

## Validation

1. Add server tests proving rank-one selection independently by mode.
2. Verify `(p)worker` and `(d)worker` become replica counts, while `(p)tp` and
   `(d)tp` become GPUs per worker/pod; test missing and non-numeric values.
3. Verify the completed-run API and UI render both mode values and the guidance.
4. Exercise the full fake-adapter browser path at desktop and narrow widths with
   Playwright MCP, including keyboard focus and no page-level horizontal overflow.
5. Run the configured formatter, linter, type checker, tests, integration,
   build, `make check`, and `git diff --check` gates.

## What Would Change This Decision

- AIConfigurator publishes a stable native Kubernetes deployment contract that
  supersedes these fields.
- Product requirements ask for actual manifest generation or cluster-specific
  scheduling validation, rather than planning guidance.
- The result schema no longer exposes the four topology fields consistently.

## Links

- Related requirements: User request; `docs/project-brief.md` estimate warning
  and generated-artifact boundaries.
- Related decisions: ADR-004 aggregated/disaggregated comparison.
- Related tasks: TASK-008 comparison; proposed follow-up topology display task.
- Supersedes or superseded by: None.
