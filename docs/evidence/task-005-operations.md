# TASK-005 Evidence: Operations, Container, and Kubernetes Delivery

## Checks executed

- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src`, and
  `uv run pytest`: all passed (8 tests; only upstream TestClient deprecation
  warnings).
- `docker build --platform linux/amd64 -t serving-configuration-portal:local .`:
  passed with the pinned Python 3.11 base and `aiconfigurator==0.11.0` plus
  `plotext==5.3.2`.
- The image starts as UID/GID `10001:10001`. `/health/live` and `/health/ready`
  return `{"status":"ok"}`; `/metrics` exposes bounded portal counters and
  gauges.

## Real container flow

On 2026-09-17, a containerized request used:

```json
{"model":"Qwen/Qwen3-32B-FP8","system":"h200_sxm","total_gpus":8,
 "ttft":1000,"tpot":10,"isl":3000,"osl":512}
```

The API returned `202`, completed in about 8 seconds, returned five normalized
rows across `agg` and `disagg`, and reported `source_version` `aiconfigurator-0.11.0`.
The run-scoped artifact endpoint returned a 95 KiB ZIP containing generated CSV,
YAML, scripts, and `k8s_deploy.yaml` files. The SDK requires output staging under
`/tmp`; the adapter copies that generated tree into the server-owned run directory.

Observed metrics after the run included:

```text
portal_runs_submitted_total 1.0
portal_runs_active 0.0
portal_runs_queued 0.0
portal_runs_completed_total 1.0
portal_runs_failed_total 0.0
```

The duration gauge `portal_run_last_duration_seconds` was also present with a
positive observed value.

Container logs were JSON-formatted and included the accepted run event, run ID,
status, and timestamp. AIConfigurator diagnostic logs remain server-side; artifact
contents are not logged.

The same flow under `--cpus=2 --memory=4g` completed successfully. Four probe
samples during the sweep kept `/health/live` below 4 ms and `/health/ready` below
5 ms; readiness stayed healthy while the worker was running.

`kubectl apply --dry-run=client -f deploy/portal.yaml` passed for both Deployment
and Service (no resources were changed).

## Kubernetes validation boundary

`deploy/portal.yaml` defines one `Recreate` replica, startup/liveness/readiness
probes, 2 CPU/4 GiB requests and limits, non-root UID/GID plus `fsGroup: 10001`,
read-only root filesystem, dropped capabilities, 30-second termination grace, and
size-limited `emptyDir` volumes. The local kubeconfig targets an EKS cluster whose
AWS exec credential is unavailable, so no live rollout or cluster mutation was
attempted; local-cluster service routing and restart evidence remain open for
TASK-006.
