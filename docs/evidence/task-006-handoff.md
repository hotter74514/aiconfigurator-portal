# TASK-006 Evidence: Handoff Validation

## Playwright MCP browser flow

On 2026-09-17, Playwright MCP opened `http://127.0.0.1:18080/` at the default
desktop viewport. The page title was `Serving Configuration Portal`; the default
Qwen/H200 form was valid and submitted through the visible **Estimate
configurations** button. The status progressed to `Run running…` and then
`Completed with 6 configurations.` The rendered table contained ordered `agg` and
`disagg` rows with throughput, TTFT, TPOT, and GPU values, and the run-scoped
**Download generated artifacts** link was visible.

The first browser pass exposed a native HTML validation issue: number inputs with
`min="0.001"` defaulted to an implicit integer step, making `1000` and `10`
invalid. Adding `step="any"` fixed the form; `form.checkValidity()` then returned
true and the same flow completed successfully. A favicon 404 was also removed with
an inline empty favicon declaration.

The browser run used the required Playwright MCP tools. No alternate browser driver
or external system was used.
