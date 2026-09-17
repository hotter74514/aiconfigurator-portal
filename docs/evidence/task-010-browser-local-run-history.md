# TASK-010 Evidence — Browser-Local Run History

## Status

The task is complete. Browser-local history is implemented without a server-wide run
enumeration endpoint. The client stores at most 20 validated entries containing an
opaque run ID, client submission time, and the minimum request summary needed to
restore the form.

## Automated client evidence

Exact command:

```text
make client-test
```

Observed on 2026-09-17: 3 Node tests passed. They cover malformed JSON and object
storage, valid-entry parsing, the 20-entry cap, newest-first ordering, duplicate
replacement, one-hour expiry, and unknown-ID pruning.

The implementation uses `src/portal/static/history.mjs` for pure history operations.
`src/portal/static/portal.mjs` catches localStorage read/write/remove failures, renders
saved values with DOM text/value properties, revalidates IDs through the existing
status endpoint, and preserves entries after transient network failures. No new
server list-runs endpoint was added; `GET /api/runs` remains unsupported.

## Application checks

Exact commands:

```text
make format
make lint
make typecheck
make test
make integration
git diff --check
```

Observed on 2026-09-17: Ruff reported all files formatted and all lint checks passed;
mypy reported no issues in 10 source files; pytest reported `24 passed` with the two
existing TestClient deprecation warnings; the integration marker reported `1 passed`;
and `git diff --check` reported no errors.

## Playwright MCP evidence

The required Playwright MCP browser exercised `http://127.0.0.1:8767/` against a
local fake adapter, so this evidence validates the UI/storage lifecycle only and is
not real AIConfigurator evidence.

- Submitted the documented form and observed `Completed with 2 configurations.`;
  the history list showed one `(completed)` entry.
- Navigated away and refreshed the page. The saved entry was revalidated through
  `/api/runs/{run_id}` and remained visible as `(completed)`. Selecting it restored
  the model field and rendered the two result rows without submitting a new run.
- Used the clear action. The list became empty, the empty-state text appeared, the
  button became disabled, and `localStorage.length` was `0`.
- Injected one valid completed ID, one unknown 32-character ID, and one old entry;
  after reload only the valid completed entry remained. The unknown status check
  correctly returned 404 and was pruned. The browser recorded that expected 404 as a
  failed network resource, not a JavaScript exception.
- At viewport `390x844`, the form, status, shared-capacity text, recent-run controls,
  and completed result path remained reachable; the status was `Completed with 2
  configurations.` and two result rows were present. Playwright keyboard traversal
  from the Model field observed `model → system → total_gpus → ttft → tpot → isl →
  osl → submit`; pressing Enter on the focused Clear browser history button removed
  the entry and restored the empty state.
- At the same `390x844` viewport, reopening the saved run exposed the download link;
  Playwright received `run-f65c2f407b304f399d8ca39fa99b2e17-artifacts.zip` from the
  run-scoped artifact URL.
- Created two Playwright browser contexts, cleared both stores, and populated only
  the first with a valid completed run. After reload, the first context showed one
  history item and the second showed zero; their stored JSON values remained separate.

The initial real-adapter browser attempt displayed the sanitized
`ModuleNotFoundError: No module named 'aiconfigurator'` failure in the macOS dev
environment, confirming that dependency failure remains recoverable and is stored as
a browser-known failed run. The fake-adapter success path was used only for the
history restore and result rendering checks.
