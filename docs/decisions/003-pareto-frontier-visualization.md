# ADR-003: Pareto Frontier Visualization Source

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

AIConfigurator `0.11.0` generates one or more `pareto_frontier.png` artifacts during
the verified sweep, while the portal API currently retains only normalized top-N
rows. A Pareto visualization must represent the same completed run and must not
claim that a frontier reconstructed from incomplete top-N data is the full search
frontier.

## Decision Drivers

- Preserve the semantics of the pinned AIConfigurator result.
- Avoid adding a chart dependency or a second frontier implementation without need.
- Serve only files contained beneath the server-generated run root.
- Keep missing or changed dependency output recoverable and explicit.
- Provide an accessible exact-value fallback.

## Options Considered

### Option A: Serve the AIConfigurator-Generated PNG

- **Benefits:** Uses the full visualization produced by the same dependency run;
  avoids recomputing from incomplete normalized rows; adds no frontend dependency.
- **Costs:** The portal inherits the image's axes, labels, styling, and accessibility
  limitations; artifact paths can vary by dependency version.
- **Failure modes:** Missing, ambiguous, corrupt, or moved image; unsafe path handling.
- **Testability:** Pinned-container inventory plus contained-file endpoint tests.
- **Reversibility:** Easy to replace behind portal-owned visualization metadata.

### Option B: Recompute a Browser Chart from Top-N Rows

- **Benefits:** Full control over layout, responsiveness, labels, and accessibility.
- **Costs:** Current rows are only per-mode top-N results and may not contain the full
  frontier; a chart could be materially misleading.
- **Failure modes:** False frontier, incorrect dominance rules, and client rounding
  differences.
- **Testability:** Easy to unit test, but correctness cannot be established without
  complete source data.
- **Reversibility:** Moderate if the client representation becomes public behavior.

### Option C: Normalize the Full Frontier into a Portal-Owned Chart Contract

- **Benefits:** Correct structured data, accessible rendering, and independent visual
  design.
- **Costs:** Requires a new verified SDK/data contract and more normalization/UI work.
- **Failure modes:** Dependency schema drift and incorrect multi-objective semantics.
- **Testability:** Strong once full-frontier fixtures and dominance rules exist.
- **Reversibility:** Good behind a versioned portal-owned contract, but highest cost.

## Recommendation

Choose Option A for the optional increment. First verify the generated image count,
relative paths, parent mode, dimensions, media type, and whether it reflects the full
sweep. Add portal-owned visualization metadata with server-issued IDs, then expose a
completed-run endpoint that serves only allowlisted PNG files contained under the
run root. Render descriptive captions and alternative text, while retaining the
ranked result table as the accessible exact-value view.

If verification shows that the PNG is not the required frontier, omit the feature
until Option C has a complete SDK contract. Do not fall back silently to Option B.

## Consequences

- **Positive:** The visualization is traceable to the same run and dependency output.
- **Positive:** No chart library or incomplete Pareto computation is introduced.
- **Negative:** Visual accessibility and styling are constrained by the generated PNG.
- **Negative:** Adapter discovery must be updated if the pinned artifact layout moves.

## Validation

1. Record the pinned-container image inventory and verified semantics.
2. Test successful serving plus queued `409`, unknown/expired `404`, missing file,
   unsupported media, symlink, and path-escape cases.
3. Use Playwright MCP for desktop, narrow viewport, keyboard navigation, captions,
   fallback table, and estimate warning.

## What Would Change This Decision

- AIConfigurator exposes stable complete frontier data suitable for normalization.
- The generated image is incomplete, unreadable, inaccessible, or unstable.
- Users require interactive axis selection, filtering, or accessible point details.

## Links

- Related task: TASK-007 in `TASKS.md`
- Related decisions: ADR-001 and ADR-002
