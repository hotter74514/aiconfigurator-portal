# TASK-019 Evidence: Rank-One Topology and Kubernetes Guidance

## Decision and implementation

ADR-010 was approved and committed as `350f0e2`:

```text
docs: accept rank-one topology guidance ADR
```

The completed-run comparison payload now contains an additive `topology` block.
It independently selects `rank == 1` for `agg` and `disagg`, preserves the raw
fields `(p)worker`, `(d)worker`, `(p)tp`, and `(d)tp`, and emits per-field
unavailable reasons. Its Kubernetes sizing payload uses this explicit mapping:

```text
worker count -> pod replicas
TP           -> GPUs per worker pod
total GPUs   -> worker count * TP
```

The UI renders those values inside the existing **Aggregated vs disaggregated**
rank-one section. It also shows separate `agg`/`disagg` sizing lines and concise
KV-cache network and topology-aware scheduling guidance. The guidance does not
apply manifests, force all workloads onto one node, or claim benchmark evidence.

## Automated checks

Commands executed on 2026-09-21:

```sh
uv run pytest tests/test_comparison.py tests/test_app.py -q
# 23 passed, 2 warnings

make format
# 62 files already formatted

make lint
# All checks passed!

make typecheck
# Success: no issues found in 11 source files

make check
# Ruff, mypy, pytest: 45 passed, 2 warnings

make integration
# 1 passed, 44 deselected, 2 warnings

make client-test
# 4 passed

make build
# Docker image serving-configuration-portal:local built successfully

git diff --check
# no output; exit status 0
```

The comparison tests cover rank-one selection, signed topology deltas, worker
and TP arithmetic, and missing/non-numeric values. The application test verifies
the serialized `topology` block and disaggregated sizing values.

## Playwright MCP browser checks

The local fake-adapter app was exercised through the configured Playwright MCP
at `http://127.0.0.1:18084/`.

- Desktop: submitted the default form and observed `Completed with 2
  configurations.` The comparison section showed all four topology fields for
  both modes, `agg`/`disagg` sizing lines, Network guidance, and Scheduling
  guidance.
- The rendered fake rank-one values were `(p)worker` 1 vs 4, `(d)worker` 1 vs
  1, `(p)tp` 16 vs 4, and `(d)tp` 16 vs 16. The `disagg` sizing rendered as
  `prefill: 4 pods × 4 GPUs/pod = 16 GPUs` and
  `decode: 1 pod × 16 GPUs/pod = 16 GPUs`.
- Narrow viewport: resized to `390x844`. `document.documentElement.scrollWidth`
  remained `390`; the topology table stayed inside its `333.61px` table wrapper,
  and the sizing panels remained visible.
- Keyboard: cleared browser storage, reloaded, tabbed nine times to focus
  `#submit`, pressed Enter, and observed the same completed topology section.
- Browser console: zero errors and zero warnings for the final fresh flow.
  Network inspection showed `POST /api/runs => 202` followed by successful
  status polling with `GET /api/runs/{id} => 200`.

The browser flow used Playwright MCP as required; no alternate browser driver was
used.
