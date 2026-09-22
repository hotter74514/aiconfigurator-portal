# TASK-015 — Portal-Owned Trade-off Surface Evidence

Date: 2026-09-18

## Accepted decision and source contract

ADR-009 was accepted before implementation. The pinned
`aic-smoke:0.11.0-pinned` SDK inventory was executed with the documented
Qwen/H200 smoke inputs and returned:

```text
pareto_fronts: agg=(24, 44), disagg=(6, 62)
required columns: request_latency, tokens/s/gpu_cluster
```

The portal normalizer accepted the complete frames and produced 30 bounded
candidates and 22 cross-mode frontier points. It does not read or recompute
from the normalized top-N rows. Missing columns, non-finite values, empty unions,
and source frames above the 128-point bound return no portal chart, leaving the
SDK PNG and ranked table fallbacks intact.

The real-source check was:

```sh
docker run --rm --platform linux/amd64 --cpus=2 --memory=4g \
  -e PYTHONPATH=/tmp -v "$PWD/src/portal:/tmp/portal" \
  --entrypoint python aic-smoke:0.11.0-pinned -c '...'
```

Observed output:

```text
{'candidates': 30, 'frontier': 22, 'modes': ('agg', 'disagg')}
```

## Automated checks

```text
make check
  ruff: passed
  mypy: Success: no issues found in 11 source files
  pytest: 39 passed (2 existing dependency deprecation warnings)
  node --test tests/test_history.mjs: 3 passed
git diff --check: passed
```

The focused normalizer, API payload, cache, and application tests also passed.
The normalizer tests cover lower-latency/higher-throughput dominance, malformed
and non-finite source values, empty modes, the cardinality bound, and explicit
axis directions.

## Playwright MCP browser validation

The local fake-adapter server was exercised through Playwright MCP at 1200 px
desktop and 390 px narrow viewports. The completed flow showed:

- `Trade-off surface` / `Pareto frontier` with `FULL SWEEP / SVG` marker.
- Cobalt frontier points, slate dominated candidate, dashed connector, grid, and
  axis labels `Request latency (ms) — lower is better` and
  `Throughput (tokens/s) — higher is better`.
- `3 of 4 plotted candidates are on the Pareto frontier.` plus three exact
  frontier summary list items.
- Four point labels exposed as focusable SVG nodes with `aria-label`; keyboard
  Tab reached `agg rank 1: 2,800 tokens/s at 22,000 ms request latency, Pareto
  frontier` after 11 tabs.
- At 390 px the trade-off region remained within the 334 px content column and
  the chart, legend, summary, list, fallback note, and ranked table remained
  readable.

Screenshots captured through Playwright MCP:

- [Desktop result flow](task-015-tradeoff-desktop.png)
- [Narrow trade-off surface](task-015-tradeoff-narrow.png)

The browser server was intentionally stopped and restarted once during setup;
the console output retained connection-refused entries for that stopped server.
The successful completed flow itself rendered the chart and did not surface a
new application error.

## Limitations

AIConfigurator exposes complete per-mode frontier frames rather than the full
pre-frontier candidate sweep. The portal therefore computes dominance only over
the union of those complete per-mode frontiers. This is sufficient to show
cross-mode dominated candidates without inventing rows, but it must not be
described as the full raw search population. The original dependency PNG and
exact ranked table remain available for source-traceable fallback evidence.
