# TASK-021 Evidence: SDK Worker Column Normalization and Guidance Removal

## Root cause

The real AIConfigurator `disagg/best_config_topn.csv` uses the source columns
`(p)workers` and `(d)workers`. The portal comparison contract looks up the
canonical singular names `(p)worker` and `(d)worker`, so the values were present
in the downloaded ZIP but were reported as unavailable in the comparison view.

The adapter now normalizes those two source aliases at the DataFrame boundary.
The generated ZIP remains unchanged and continues to contain the original SDK
column names.

## Contract change

- `(p)workers` → `(p)worker`
- `(d)workers` → `(d)worker`
- Disaggregated sizing continues to calculate replicas from worker counts and
  GPUs per worker Pod from `(p)tp`/`(d)tp`.
- `network` and `scheduling` were removed from the comparison topology payload,
  UI, tests, and documentation under ADR-012.

## Automated checks

Commands executed on 2026-09-21:

```sh
uv run pytest tests/test_comparison.py tests/test_app.py -q
# 24 passed, 2 warnings

uv run ruff check src tests
# All checks passed!

node --check src/portal/static/portal.mjs
# exit status 0
```

The new normalization test uses SDK-shaped plural worker columns and verifies
that the canonical singular fields are populated without retaining duplicate
aliases.

## Minikube deployment and real API smoke test

The local `aiconfigurator` Minikube profile is an arm64 node. The current image
was rebuilt and loaded as `serving-configuration-portal:local-arm64`, then the
checked-in manifest was applied and the Deployment image was overridden for the
architecture-matched local image.

```text
kubectl apply --dry-run=client -f deploy/portal.yaml       # passed
docker buildx build --platform linux/arm64 --load \
  -t serving-configuration-portal:local-arm64 .            # passed
minikube image load serving-configuration-portal:local-arm64 \
  --profile aiconfigurator                                  # passed
kubectl rollout status deployment/serving-configuration-portal --timeout=180s
                                                             # passed
```

Observed workload state:

- Deployment: `1/1` available.
- Pod: `Running`, `0` restarts.
- `/health/live`, `/health/ready`, and `/metrics`: HTTP 200.
- Real run `e15d4f6ef6104103952a0865da5779fe`: `202` submitted and
  `completed`.
- The downloaded source CSV contained `(p)workers=2`, `(d)workers=1`,
  `(p)tp=1`, and `(d)tp=2`; after normalization the comparison response
  exposed the worker values and calculated the corresponding disaggregated
  sizing instead of reporting missing workers.
- The response topology payload contained no `network` or `scheduling` keys.
- After the final image rebuild and rollout, real run
  `9156fef6be06481ba8cf7c130de3acdb` also completed with the same normalized
  worker values and sizing.

## Browser UI checks

The deployed service was exercised through Playwright MCP after the fix:

- The table rendered `(p)worker` value `4` and `(d)worker` value `1` as
  `Available` for the default browser smoke run.
- The sizing panel rendered `prefill: 4 pods × 1 GPU/pod = 4 GPUs` and
  `decode: 1 pod × 4 GPUs/pod = 4 GPUs`.
- The topology text contained neither `Network` nor `Scheduling`.
- At `390x844`, document scroll width remained `390`; console errors and
  warnings were both zero.

The SDK emitted non-fatal version/template warnings during the smoke run; the
run completed successfully.
