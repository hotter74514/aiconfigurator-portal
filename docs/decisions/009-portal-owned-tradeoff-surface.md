# ADR-009: Portal-Owned Trade-off Surface Visualization

## Status

**Proposed**

## Decision Owner

Repository owner / take-home candidate.

## Context

The portal currently serves AIConfigurator's generated `pareto_frontier.png`
unchanged. The pinned AIConfigurator 0.11.0 artifact is a valid 800×500 image,
but its presentation is a dependency-owned two-series plot and does not provide
the requested trade-off-surface treatment: explicit frontier/dominated point
encoding, a clear "lower latency / higher throughput" explanation, and a
frontier summary list.

The same pinned SDK's `CLIResult` exposes `pareto_fronts`, a structured mapping of
complete, SLA-filtered frontier DataFrames used by the SDK itself to generate the
PNG and `pareto.csv`. This is new evidence that a portal-owned visualization can
use the full frontier rather than the portal's incomplete top-N result rows.

## Decision Drivers

- Preserve the SDK's full-sweep and SLA-filtered Pareto semantics.
- Match the requested trade-off-surface visual language without adding a runtime
  chart dependency or trusting browser-recomputed top-N data.
- Keep exact values and an accessible ranked-table fallback.
- Keep the visualization run-scoped, bounded, and safe for the existing ephemeral
  artifact lifecycle.
- Make the choice reversible if the pinned SDK schema changes.

## Options Considered

### Option A: Continue Serving the SDK PNG

- **Benefits:** No new implementation; semantics remain entirely dependency-owned.
- **Costs:** Cannot control the requested visual treatment, point semantics, or
  summary content; accessibility remains constrained by a bitmap.
- **Failure modes:** Dependency styling or dimensions change without portal control.
- **Reversibility:** Already implemented and remains a safe fallback.

### Option B: Render a Portal-Owned Chart from `CLIResult.pareto_fronts`

- **Benefits:** Uses the complete SDK-provided frontier; supports the requested
  latency/throughput axes, dominated-candidate styling, frontier connector,
  summary list, responsive layout, and accessible text/table fallback. No browser
  dependency is required if the server emits a self-contained SVG or PNG.
- **Costs:** Adds a small portal-owned renderer and a versioned normalization
  contract for the pinned SDK columns (`request_latency`, `tokens/s/gpu_cluster`,
  serving mode, and rank/configuration metadata).
- **Failure modes:** SDK column drift, invalid numeric values, oversized point
  sets, or an incorrect objective direction could create a misleading chart.
- **Reversibility:** Keep the verified SDK PNG and ranked table as fallbacks; disable
  the portal chart when the full-frontier contract cannot be normalized.

### Option C: Recompute the Frontier in the Browser from Normalized Rows

- **Benefits:** Small client-side implementation with flexible styling.
- **Costs:** The current normalized rows are top-N only and cannot prove the full
  frontier; browser recomputation would risk false dominance claims.
- **Failure modes:** Incorrect frontier, client/server rounding differences, and
  inaccessible or high-cardinality serialized data.
- **Reversibility:** Moderate once the browser contract becomes public behavior.

## Recommendation

Choose Option B. Normalize only the complete `pareto_fronts` supplied by the
pinned SDK, validate required finite numeric columns and a bounded point count,
and render a self-contained portal-owned trade-off surface. Keep the original
SDK PNG and exact ranked table available as fallback evidence. Do not derive the
frontier from top-N rows.

This supersedes the source recommendation in ADR-003 only after acceptance; the
existing contained PNG endpoint remains backwards-compatible during migration.

## Consequences

- **Positive:** The UI can match the requested trade-off surface while preserving
  full-sweep correctness and exact-value fallback behavior.
- **Negative:** The portal now owns a small visualization contract and must test
  SDK schema drift and objective direction.
- **Follow-up work:** Add a portal-owned visualization payload/asset, server-side
  normalization and validation, deterministic chart rendering, accessible summary
  text, responsive/keyboard browser checks, and fixtures from `pareto_fronts`.

## Validation

1. Run the pinned SDK smoke case and assert `pareto_fronts` contains complete
   finite frames with the required columns and bounded cardinality.
2. Unit-test normalization, latency minimization, throughput maximization,
   dominated-point classification, malformed/missing columns, and empty frames.
3. Render the chart from deterministic fixtures and verify the original SDK PNG
   and ranked table remain available when the portal chart is unavailable.
4. Use Playwright MCP at desktop and narrow widths to verify labels, frontier
   summary, accessible text, keyboard focus, and the full submit-to-result flow.
5. Re-run `make check`, image build, manifest validation, and `git diff --check`.

## What Would Change This Decision

- `pareto_fronts` is removed, incomplete, or no longer stable in the pinned SDK.
- The SDK's objective columns or SLA filtering semantics change without a
  versioned migration path.
- Users require interactive filtering or dimensions that cannot be represented by
  the bounded server-owned contract.

## Links

- Related requirements: `docs/project-brief.md`, TASK-007, TASK-014.
- Related decisions: ADR-003 (accepted source artifact), ADR-004.
- Supersedes or superseded by: Proposed replacement of ADR-003's source choice.
