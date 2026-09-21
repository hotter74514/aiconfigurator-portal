# TASK-020 Evidence: Mode-Aware Topology Semantics

## Corrected contract

ADR-011 was accepted and committed as `0afac9b`. The corrected comparison
contract now preserves the source schema by serving mode:

- `agg` rank 1 shows `tp`, `pp`, `dp`, `num_total_gpus`, and `parallel`.
- `disagg` rank 1 shows `(p)worker`, `(d)worker`, `(p)tp`, and `(d)tp` when
  supplied by the source result.
- Aggregated Pod replicas are explicitly unavailable. The portal does not infer
  them from `tp`, `num_total_gpus`, or `parallel`.
- Disaggregated sizing uses worker count as Pod replicas and TP as GPUs per
  worker Pod.
- Generic Network and Scheduling guidance is excluded; the portal only exposes
  source-derived topology and Kubernetes sizing.

The fake adapter no longer injects synthetic `(p)/(d)` fields into its agg row.

## Automated checks

Commands executed on 2026-09-21:

```sh
uv run pytest tests/test_comparison.py tests/test_app.py -q
# 23 passed, 2 warnings

make lint
# All checks passed!

make typecheck
# Success: no issues found in 11 source files

make check
# Ruff, mypy, and 45 pytest tests passed; 2 warnings

make client-test
# 4 passed

make integration
# 1 passed, 44 deselected, 2 warnings

make build
# Docker image serving-configuration-portal:local built successfully

git diff --check
# no output; exit status 0
```

The mode-aware tests verify rank-one selection, actual aggregated fields,
absence of synthetic `(p)/(d)` agg fields, explicit aggregated sizing
unavailability, disaggregated worker/TP arithmetic, and invalid source values.

## Playwright MCP browser checks

The corrected local fake-adapter app was exercised through the configured
Playwright MCP at `http://127.0.0.1:18084/`.

- Desktop/narrow: the topology table showed aggregated `tp`, `pp`, `dp`,
  `num_total_gpus`, and `parallel`, followed by disaggregated `(p)worker`,
  `(d)worker`, `(p)tp`, and `(d)tp`.
- The aggregated sizing panel showed:
  `Pod replicas: Unavailable (agg result does not expose worker or replica
  fields; Pod replicas cannot be derived from tp or num_total_gpus)`.
- The disaggregated sizing panel showed `prefill: 4 pods × 4 GPUs/pod = 16
  GPUs` and `decode: 1 pod × 16 GPUs/pod = 16 GPUs`.
- At `390x844`, `document.documentElement.scrollWidth` remained `390`.
- Keyboard navigation focused `#submit` after nine Tab presses; Enter submitted
  successfully and rendered the corrected topology section.
- After clearing browser-local history and reloading, the final fresh flow had
  zero console errors and zero warnings. The submission returned `202` and
  status polling returned `200`.

No alternate browser driver was used.
