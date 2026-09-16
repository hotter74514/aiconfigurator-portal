# TASK-002 Evidence: Application Skeleton

## Delivered

- `pyproject.toml` defines the Python 3.11 package, FastAPI/Uvicorn runtime,
  optional Linux-only AIConfigurator dependencies, and development tools.
- `uv.lock` records the resolved dependency graph.
- `src/portal/adapters.py` defines the typed `RunRequest`, `ConfigurationRow`,
  `RunResult`, and `AiconfiguratorAdapter` boundary plus a deterministic fake
  adapter. The real AIConfigurator package is not imported during app startup.
- `src/portal/app.py` provides an app factory with a liveness endpoint and metadata
  endpoint. Run lifecycle and UI work remain in later tasks.
- `tests/test_app.py` covers app factory behavior and fake artifact generation.
- `Makefile` now has real format, lint, typecheck, test, integration, and build
  commands.

## Checks

Executed successfully on macOS Python 3.11.14:

```text
make format       -> 24 files already formatted
make lint         -> All checks passed
make typecheck    -> Success: no issues found in 3 source files
make test         -> 2 passed
make integration  -> 1 passed, 1 deselected
make build        -> source distribution and wheel built successfully
git diff --check  -> passed
```

Pytest reports two upstream deprecation warnings from the current FastAPI/Starlette
TestClient integration (`httpx` compatibility and AnyIO's BlockingPortal alias).
They do not fail the configured checks and are recorded for dependency maintenance.

## Remaining Scope

The real adapter is intentionally still behind the protocol; the Linux container
smoke evidence in TASK-001 is the external contract. No job queue, result polling,
artifact retention, browser UI, metrics, or Kubernetes image is claimed complete by
this task.
