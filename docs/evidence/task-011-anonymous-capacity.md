# TASK-011 Evidence — Anonymous Shared Capacity

## Status

The aggregate capacity endpoint and visibility-aware UI are implemented and verified.
The task is complete. Playwright MCP became available on retry, and the pinned Linux
container completed a real AIConfigurator sweep with capacity requests measured
during the run.

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

## Playwright MCP browser evidence

The Playwright MCP browser loaded `http://127.0.0.1:8765/` and showed the shared
capacity heading, live banner, no-account/no-reservation wording, and form labels.

Two isolated browser contexts submitted concurrently. The two responses were
`202` with one `running` and one `queued`; both contexts then received the exact same
aggregate payload:

```json
{"active":1,"queued":1,"active_capacity":1,"queue_capacity":1,"admission_open":false}
```

The visible banner rendered:
`Shared capacity is full: 1 run active; 1 waiting. New submissions may be rejected; retry later.`

For visibility behavior, the page was observed with `document.visibilityState` set to
`visible`, then a browser `visibilitychange` event changed it to `hidden`. During a
three-second hidden interval, capacity fetch count stayed at `21` (`hiddenDelta: 0`);
after returning to `visible`, the count increased to `22`, confirming resume behavior.
This event simulation was used because switching MCP tabs does not background a page
in this browser surface.

At viewport `390x844`, the accessibility snapshot retained all form controls and the
shared-capacity region within the responsive layout. Keyboard Tab navigation reached
the `Estimate configurations` button after the labeled inputs, and Enter initiated a
run; the page showed `Run running…` and disabled the button.

After a fresh page navigation with the service available, Playwright MCP reported
`Total messages: 0 (Errors: 0, Warnings: 0)`. Earlier connection-refused messages
were from intentionally stopping and restarting the local test service and are not
part of the fresh-page check.

## Local endpoint observation

With a local fake-adapter Uvicorn service configured for one active and one queued
run, the endpoint returned:

```json
{"active":0,"queued":0,"active_capacity":1,"queue_capacity":1,"admission_open":true}
```

While a run was active, five consecutive capacity requests completed in
`0.001284s`, `0.001060s`, `0.001118s`, `0.000993s`, and `0.001005s`.

## Pinned-container real-sweep observation

The pinned image was started with:

```text
docker run --rm --name task-011-real -p 8766:8080 serving-configuration-portal:local
```

The documented request was submitted to `http://127.0.0.1:8766/api/runs` with model
`Qwen/Qwen3-32B-FP8`, system `h200_sxm`, `total_gpus=32`, `ttft=1000`, `tpot=10`,
`isl=3000`, and `osl=512`. It returned run ID
`04da00d5e5134eb9b2acf0a6e7045bc1` with `202`/`running`; the final status was
`completed` with `source_version=aiconfigurator-0.11.0`.

The run timestamps were `15:21:46.965854Z` to `15:21:56.875646Z` (approximately
`9.91s`). Ten capacity requests during the sweep returned HTTP 200 in
`0.004087s`, `0.001909s`, `0.002000s`, `0.003048s`, `0.002159s`, `0.003207s`,
`0.002951s`, `0.002821s`, `0.001961s`, and `0.002612s`.

## Browser blocker history

The following Playwright MCP calls were attempted:

- Navigate to `http://127.0.0.1:8765/`.
- List tabs and capture a page snapshot.
- Connect through the repository browser runtime for the same local URL.

An earlier attempt was blocked by a competing MCP Chrome profile lock. On retry the
lock cleared and the required Playwright MCP browser scenarios were completed; no
alternate browser automation tool was used.
