# TASK-011 Evidence — Anonymous Shared Capacity

## Status

The aggregate capacity endpoint and visibility-aware UI are implemented. The task
remains in progress because the required Playwright MCP browser validation could not
start: the configured Chrome profile was locked by another MCP process, and the
browser runtime reported no available browser. No alternate browser automation tool
was used.

## Implemented behavior

- `GET /api/capacity` returns exactly `active`, `queued`, `active_capacity`,
  `queue_capacity`, and `admission_open`.
- Counts are read under the `RunManager` lock and reflect this process only.
- `admission_open` is false while shutting down or when active plus queued work has
  reached configured capacity. It is informational and does not reserve a slot.
- The page displays neutral shared-pressure text and states that there are no
  accounts, ownership, reservations, fairness, or quotas.
- Capacity refreshes at the existing two-second interval only while
  `document.visibilityState` is `visible`; hidden pages clear the scheduled timer.
- The page renders all server-derived text with `textContent`.

## Automated evidence

Exact targeted command:

```text
uv run pytest tests/test_app.py -q -k 'capacity_endpoint or app_factory_exposes_liveness'
```

Observed result: `2 passed, 12 deselected, 2 warnings`.

The capacity test covered idle, active, queued/saturated, active-after-queue,
completed/idle, shutdown, configured capacities, and exact allowlisted response
fields. The full application test suite then passed:

```text
make format
make lint
make typecheck
make test
make integration
git diff --check
```

Observed results: Ruff format reported 45 files already formatted; Ruff lint passed;
mypy reported no issues in 10 source files; pytest reported `24 passed, 2 warnings`;
pytest integration reported `1 passed, 23 deselected, 2 warnings`; `git diff --check`
reported no errors.

## Local endpoint observation

With a local fake-adapter Uvicorn service configured for one active and one queued
run, the endpoint returned:

```json
{"active":0,"queued":0,"active_capacity":1,"queue_capacity":1,"admission_open":true}
```

While a run was active, five consecutive capacity requests completed in
`0.001284s`, `0.001060s`, `0.001118s`, `0.000993s`, and `0.001005s`.

This is a local fake-worker responsiveness observation, not evidence of a real
AIConfigurator sweep. The real-sweep latency observation and browser scenarios are
unverified until Playwright MCP is available.

## Browser blocker

The following Playwright MCP calls were attempted:

- Navigate to `http://127.0.0.1:8765/`.
- List tabs and capture a page snapshot.
- Connect through the repository browser runtime for the same local URL.

Each MCP connection attempt reported that the browser was already in use by
`/Users/sean_yang/Library/Caches/ms-playwright-mcp/mcp-chrome-e7abbf9`; the runtime
listed no available browsers. The process check showed existing `playwright-mcp`
and Chrome processes using that profile. They were left untouched.
