# ADR-011: Mode-Aware Topology Semantics

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

The accepted ADR-010 assumed that rank-one `agg` and `disagg` rows both expose
`(p)worker`, `(d)worker`, `(p)tp`, and `(d)tp`. The actual aggregated result
provided by the repository owner has a different schema: it exposes fields such
as `tp`, `pp`, `dp`, `num_total_gpus`, and `parallel`, but does not expose the
prefill/decode worker fields. Therefore an aggregated row cannot support the
same worker-to-Pod calculation as a disaggregated row.

The current implementation is misleading in two ways: it injects synthetic
`(p)/(d)` fields into the fake aggregated adapter fixture, and it renders
aggregated Pod sizing as if those fields were supplied by AIConfigurator. This
violates the result-normalization boundary and can lead an operator to deploy
the wrong Kubernetes shape.

The portal must distinguish source fields by serving mode. It must never infer
an aggregated Pod count from `tp`, `num_total_gpus`, or the `parallel` string
unless AIConfigurator explicitly publishes a worker/replica contract.

## Decision Drivers

- Reflect the actual AIConfigurator schema for each serving mode.
- Never fabricate or infer worker counts from TP, GPU count, or parallel labels.
- Preserve useful disaggregated sizing when `(p)/(d)` fields are actually present.
- Show aggregated `tp`, `pp`, `dp`, and GPU fields without presenting them as Pod
  replica counts.
- Keep unavailable values and reasons explicit in the API and UI.
- Correct ADR-010 without expanding into manifest generation or cluster-specific
  scheduling validation.

## Options Considered

### Option A: Use a mode-aware topology contract

- Benefits: Matches the observed schema; preserves disaggregated worker sizing;
  makes aggregated Pod-count limitations explicit.
- Costs: The comparison view has different field sets and guidance per mode.
- Failure modes: Future SDK schema changes still require adapter evidence and
  fixture updates.
- Reversibility: Good; the additive mode-aware block can be versioned later.

### Option B: Infer one aggregated Pod from `tp` or `num_total_gpus`

- Benefits: Produces a complete-looking K8s recommendation from every agg row.
- Costs: Adds an unsupported deployment assumption and conflates parallel width
  with replica count.
- Failure modes: Wrong Pod count, wrong GPU request, and misleading scheduling
  advice for runtimes that use another process or replica model.
- Reversibility: Poor because downstream users may treat the inferred shape as
  an authoritative deployment contract.

### Option C: Remove all topology guidance

- Benefits: Avoids incorrect inference for agg.
- Costs: Throws away valid `(p)/(d)` worker sizing present in disagg results and
  does not answer the user's deployment-planning question.
- Failure modes: Users independently reconstruct the same semantics with less
  visible evidence.
- Reversibility: Easy, but loses useful supported information.

## Recommendation

Choose Option A and supersede ADR-010.

- For `disagg`, read `(p)worker`, `(d)worker`, `(p)tp`, and `(d)tp` only when
  those exact source fields exist. Worker counts determine prefill/decode Pod
  replicas and TP determines GPUs per worker Pod.
- For `agg`, show the actual `tp`, `pp`, `dp`, `num_total_gpus`, and `parallel`
  values from rank 1. Do not display synthetic `(p)/(d)` values and do not
  derive an aggregated Pod count. State that Pod replicas require an explicit
  worker/replica contract or deployment artifact.
- Keep network and scheduling advice conditional: TP placement constraints apply
  where a TP worker group is known; KV-cache prefill/decode network advice
  applies to disagg; all estimates still require cluster benchmarking.

The repository owner approved this recommendation. Implementation may proceed
within the scope and validation gates below.

## Consequences

- Positive: The portal stops presenting fabricated agg Pod sizing.
- Positive: The API truthfully separates aggregated parallelism from
  disaggregated worker topology.
- Positive: The fake adapter becomes a faithful fixture instead of a source of
  unsupported fields.
- Negative: Aggregated rows will show Pod count as unavailable until the SDK or
  generated artifact supplies an explicit worker/replica field.
- Follow-up work: Update the comparison payload, fake adapter, tests, UI copy,
  task status, and evidence; mark ADR-010 Superseded after acceptance.

## Validation

1. Add an agg fixture matching the supplied columns and verify no `(p)/(d)`
   fields are synthesized.
2. Add a disagg fixture with the four worker/TP fields and verify worker-to-Pod
   and TP-to-GPU arithmetic.
3. Verify the completed-run API and UI show mode-specific values and explicit
   unavailable reasons.
4. Exercise desktop, 390 px, keyboard, and console/network flows with Playwright
   MCP.
5. Run the configured format, lint, type, test, integration, build, `make check`,
   and `git diff --check` gates.

## What Would Change This Decision

- AIConfigurator publishes a documented aggregated worker/replica contract.
- A generated agg deployment artifact provides a verified Pod/replica mapping.
- Product requirements explicitly request a separately documented runtime
  assumption for aggregated deployment sizing.

## Links

- Supersedes: ADR-010, pending acceptance of this record.
- Related decision: ADR-004 aggregated/disaggregated comparison.
- Related task: TASK-019 rank-one topology and Kubernetes sizing guidance.
- Evidence: Repository owner's supplied aggregated result schema.
