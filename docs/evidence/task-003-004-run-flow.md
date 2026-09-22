# TASK-003/004 Evidence: Async Run and Result Flow

## Delivered

- `RunManager` admits one active run plus four queued runs, transitions queued →
  running → completed/failed, rejects excess capacity, and applies a configurable
  timeout.
- `POST /api/runs` validates model/system/GPU/SLA/token inputs and returns `202`
  with an opaque ID and polling URL.
- `GET /api/runs/{id}` returns lifecycle state and normalized result rows; invalid
  IDs and unknown runs return `404`.
- The real adapter lazily imports `aiconfigurator.cli_default`, passes `strict_sla`
  and `top_n=5`, and normalizes version-specific DataFrame cells into scalar portal
  metrics.
- The browser page submits defaults, polls using the server-provided interval,
  renders a rank/mode/throughput/TTFT/TPOT/GPU table, and links only completed-run
  artifacts.
- ZIP creation rejects symlinks/path escapes and includes only regular files beneath
  the server-generated run directory.
- Terminal runs expire after one hour; UUID-named orphan directories are removed at
  manager startup.

## Checks

Executed successfully:

```text
make ci                -> Ruff, mypy, 7 pytest tests, integration test, uv build passed
git diff --check       -> passed
wheel inspection       -> portal/templates/index.html included
```

The test suite uses a deterministic fake worker for speed and isolation. Real SDK
execution remains validated by TASK-001's Linux image smoke; a combined portal image
and Kubernetes probe/load test is intentionally TASK-005.

Pytest still reports two upstream FastAPI/Starlette TestClient deprecation warnings;
they do not fail the configured checks.
