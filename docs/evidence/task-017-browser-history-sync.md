# TASK-017 Evidence: Browser-Local History Synchronization

## Scope

The existing ADR-006 browser-local history boundary remains in place. This change
only synchronizes the capped `localStorage` index between same-origin tabs and
prevents an older asynchronous revalidation from restoring entries after a clear.
No server-side list-runs endpoint, account, cookie, or ownership claim was added.

## Checks

- `make client-test` — passed; 4 Node tests, including concurrent-entry merge.
- `make check` — passed; Ruff, strict mypy, 43 pytest tests, and 4 Node tests.
- `git diff --check` — passed.

## Playwright MCP observation

Date: 2026-09-19 (Asia/Taipei)

1. Started the local portal with `uv run uvicorn portal.app:app --host
   127.0.0.1 --port 8765`.
2. Used the repository-configured Playwright MCP server with two tabs sharing one
   isolated browser profile at `http://127.0.0.1:8765/`.
3. Reloaded both tabs, cleared browser history, and waited one second. Both tabs
   stayed empty and `localStorage` remained `null`; stale initial revalidation did
   not restore entries.
4. Filled different model values in both tabs and clicked **Estimate
   configurations** concurrently with Playwright MCP. Both tabs rendered the same
   two entries, and the shared storage value contained exactly two entries. The
   local dependency failure was expected because the host does not install the
   Linux-only `aiconfigurator` package; each submitted run still exercised the
   history write path.
5. `browser_console_messages(level="error", all=true)` reported zero errors.
