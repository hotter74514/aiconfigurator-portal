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

## Live Minikube deployment

On 2026-09-17, the checked-in image and manifest were deployed to Minikube v1.39.0
with Kubernetes v1.37.0. `kubectl rollout status` completed with one ready pod and
zero restarts. Service-routed live/readiness probes and metrics returned HTTP 200.
A real `Qwen/Qwen3-32B-FP8`, 8 × `h200_sxm` request completed with five ranked
results from `aiconfigurator-0.11.0`; its artifact endpoint returned a 97,617-byte
ZIP. Exact deployment commands and observations are recorded in
`docs/evidence/task-005-operations.md`.

## Owner confirmation

The repository owner subsequently confirmed that TASK-006 validation has no known
issues. This closes TASK-006 and Stage 5 for planning purposes. The granular
checkboxes in `docs/verification-checklist.md` remain the detailed evidence index;
any item that needs a separately recorded command, viewport, or observation should
be filled in when that evidence is available.
