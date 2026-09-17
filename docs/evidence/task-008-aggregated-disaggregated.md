# TASK-008 Evidence: Aggregated and Disaggregated Comparison

## Verified contract

The pinned AIConfigurator smoke evidence shows that `best_configs` contains
independently ranked `agg` and `disagg` frames. The portal comparison therefore
selects `rank == 1` separately for each mode; it does not compare flattened row
positions or infer a cross-mode rank.

The completed-run payload now includes an additive `comparison` block with:

- rank-one absolute values for `tokens/s`, `ttft`, `tpot`, and `num_total_gpus`;
- signed deltas defined as `disagg - agg`, with percentage relative to
  `abs(agg)`;
- absolute and percentage deltas rounded half-up to two decimal places;
- explicit per-metric reasons for missing values or a zero `agg` baseline; and
- an overall `available` flag without declaring a universal winner.

The raw ranked result rows and the real-benchmark warning remain unchanged.
The browser table renders unavailable values as `Unavailable` and uses DOM text
properties for all server-provided values.

## Automated checks

Commands executed on 2026-09-17:

```sh
uv run pytest tests/test_comparison.py -q
# 4 passed

make format
# 41 files already formatted

make lint
# All checks passed!

make typecheck
# Success: no issues found in 9 source files

make test
# 16 passed, 2 warnings

make integration
# 1 passed, 15 deselected, 2 warnings

make check
# docs, Ruff, mypy, and pytest all passed

git diff --check
# no output; exit status 0
```

The comparison tests cover rank-one selection, positive and negative signed
deltas, deterministic rounding, missing mode, missing metric, and zero-baseline
percentage behavior. The API test verifies both modes and the serialized
percentage delta. The deterministic fake adapter supplies one rank-one row for
each mode so the completed-run API and page contract are exercised without the
Linux-only SDK.

## Playwright MCP browser checks

On 2026-09-17, the local fake-adapter app was exercised through the configured
Playwright MCP at `http://127.0.0.1:18084/`.

- Desktop: submitted the default form and observed `Completed with 2
  configurations.` The completed view showed the **Aggregated vs disaggregated**
  heading, both rank-one mode values, absolute deltas, signed percentage deltas,
  the delta definition, the no-universal-winner warning, and the raw ranked table.
- Narrow viewport: resized to `390x844`. The form, comparison heading/status,
  warning, and values remained visible. The comparison table measured 424.54 CSS
  pixels inside a 374 pixel overflow container; `document.documentElement.scrollWidth`
  remained 390, so the page itself did not horizontally overflow.
- Keyboard: navigated to a fresh page, pressed `Tab` eight times, and confirmed
  the **Estimate configurations** button was focused. Pressing `Enter` submitted
  the form and the completed comparison appeared.
- Browser console: zero errors and zero warnings. Network inspection showed one
  `POST /api/runs` followed by status polling; no duplicate submission occurred.

No alternate browser driver was used.
