# Verification Checklist

Record exact commands, versions, inputs, observed outputs, and dates as work is
completed. A checkbox without evidence is not a pass. Commands marked "configure in
Stage 1" describe the intended stable Make target, not a command already verified.

## Reproducibility and Dependency Proof

- [x] A clean checkout installs only from the committed lockfile and documented
  Linux x86-64 container build.
- [x] README lists required Docker/kubectl/cluster tools, tested versions, startup
  commands, safe example values, and first-run network/cache behavior.
- [x] The pinned AIConfigurator version completes the documented
  `Qwen/Qwen3-32B-FP8`, 32 × `h200_sxm` SDK smoke run with explicit TTFT/TPOT,
  `top_n`, and `save_dir`.
- [x] Evidence records the SDK result keys/columns, generated artifact tree, runtime,
  peak memory when practical, and SLA-filter behavior.
- [x] The image and manifest contain no credentials, private data, local paths,
  generated run output, writable source tree, or floating application dependencies.

## Automated Checks

- [x] `make format` reports no changes.
- [x] `make lint` passes.
- [x] `make typecheck` passes.
- [x] `make test` passes unit and API integration tests.
- [x] `make build` builds the Linux x86-64 image.
- [x] `make integration` exercises the containerized fake
  dependency path and the separately documented real smoke path.
- [x] `make check` passes without skipping configured checks.
- [x] `git diff --check` passes.

## API and Lifecycle Behavior

- [x] Valid input returns `202`, opaque run ID, status URL, and recommended poll
  interval before the worker completes.
- [x] Invalid GPU count/TTFT/TPOT/token lengths, unknown systems, and oversized model
  identifiers return stable validation errors and do not create work.
- [x] Status follows only queued → running → completed/failed and unknown/malformed
  IDs return `404` without filesystem disclosure.
- [x] One active plus four queued runs are admitted; the next returns `429` and a
  retry hint while queue memory remains bounded.
- [x] SDK exception, no-feasible-config result, unexpected process exit, and timeout
  produce sanitized, actionable terminal failures without killing the API.
- [x] SIGTERM stops admission/readiness, gives active work the documented grace
  period, and does not claim recovery if the job is killed.

## Results, Artifacts, and Cleanup

- [x] Completed results contain normalized ranked rows; the real smoke dependency
  returns the available top-N rows for this input and the required metrics.
- [x] Completed results contain at least five ranked rows when the real dependency
  supplies them, with mode, throughput, TTFT, TPOT, and verified topology fields.
- [x] SLA-violating rows are excluded or visibly marked according to the behavior
  established in TASK-001.
- [x] Download before completion returns `409`; unknown/expired returns `404`;
  completed returns a run-scoped ZIP with safe headers and expected generated files.
- [x] Attempts to influence a run path or include sibling-run files fail; only files
  under the server-generated run root are archived.
- [x] A completed run exposes one verified same-run Pareto PNG with caption,
  alternative text, scope/axis notes, and the ranked-table exact-value fallback;
  ambiguous, missing, non-PNG, symlink, and path-escape assets are not served.
- [x] A completed run exposes a bounded `tradeoff_surface` from complete SDK
  `pareto_fronts` frames with explicit lower-latency/higher-throughput directions,
  cross-mode frontier classification, and safe fallback when the source contract
  is malformed or empty.
- [x] One-hour TTL cleanup removes terminal metadata/files; active work is retained;
  startup removes or reconciles documented orphan state.
- [x] Full/unwritable temporary storage fails the run clearly while live/ready remain
  semantically correct.

## Observability and Resource Behavior

- [x] `/health/live` tests web-process/event-loop health and remains responsive
  during a sweep.
- [x] `/health/ready` tests initialization/admission lifecycle, becomes false during
  shutdown, and does not flap merely because the queue is busy.
- [x] `/metrics` exposes low-cardinality submitted/completed/failed/rejected totals,
  active work, queue depth, and duration without run/model/user labels.
- [x] `/api/capacity` exposes only active/queued counts, configured active/queue
  capacities, and aggregate admission state for idle, active, saturated, and
  shutdown service states.
- [x] JSON logs include timestamp, level, event, run ID, terminal status, duration,
  and safe error category; stack traces stay server-side and artifact bodies are not
  logged.
- [x] Under the manifest CPU/memory limits, repeated live/ready/status probes remain
  within the recorded latency target during a real sweep; CFS throttling/resource
  observations and any tuning are recorded.

## Container and Kubernetes

- [x] Runtime image uses a pinned base/dependencies, non-root user, minimal runtime
  contents, explicit writable directories, and a local healthcheck.
- [x] `kubectl apply --dry-run=client -f deploy/` succeeds (no resources changed).
- [x] Deployment has one replica, `Recreate`, startup/live/ready probes, explicit
  requests/limits, termination grace, bounded `emptyDir`, and restrictive security
  context compatible with the application.
- [x] Service routing, rollout, logs, metrics, real run, result polling, and ZIP
  download succeed on an available local cluster. TASK-012 used an arm64 local-only
  image matching the arm64 Minikube node while retaining the amd64 release image.
- [x] Pod deletion during a run demonstrates the documented loss/`404` behavior
  after restart; no durability claim is made. Run
  `0a0713af68bb4a8b935926b58e7f3d23` was running before deletion and returned `404`
  from the replacement pod.

## Browser Validation — Playwright MCP Only

- [x] Desktop viewport: submit the documented default, observe queued/running,
  inspect ordered results and estimate warning, and download/inspect the ZIP.
- [x] Narrow viewport: all form controls, status, result fields, warning, and download
  remain usable; record viewport and screenshot only if useful for evidence. TASK-010
  exercised the history controls, completed result path, and ZIP download at `390x844`
  (see `docs/evidence/task-010-browser-local-run-history.md`).
- [x] TASK-011 Playwright MCP coverage: two isolated contexts observe the same
  aggregate pressure, the capacity banner shows saturation, visibility-aware polling
  pauses and resumes, and keyboard focus reaches and activates submission.
- [x] Keyboard-only: labels, focus order, submission, status announcement, result
  navigation, retry, and download are usable. TASK-012 verified the labeled
  input-to-submit focus order, Enter submission, completed result, history controls,
  retry navigation, and focus reaching the run-scoped download link. The configured
  MCP server now uses `--isolated`; Enter saved and inspected the ZIP successfully
  with no download failure.
- [x] Client and server validation: invalid field and dependency failure each show a
  recoverable message without a browser console error. Native invalid-GPU validation
  produced no POST; the fresh dependency-failure run showed the sanitized
  `RuntimeError: AIConfigurator dependency unavailable` message, kept Submit enabled,
  and recovered to a completed result after keyboard retry with zero console errors.
- [x] Polling stops after completed/failed state and does not issue duplicate
  submissions on repeated clicks. Two Enter presses produced one POST and one terminal
  GET; the request list stayed unchanged during a further three-second interval.
- [x] If Playwright MCP is unavailable, record the blocker and leave these unchecked;
  do not substitute another browser automation tool. Playwright MCP remained the
  only browser automation; the project-scoped isolated-profile configuration kept
  the transport alive through keyboard download completion.

## Trust and Product Safety

- [x] User input is mapped to typed SDK arguments and never interpolated into a shell
  command, log format string, artifact path, or rendered unsafe HTML.
- [x] Generated manifests are never automatically applied and every result/download
  experience says predictions require real benchmark validation.
- [x] No authentication is represented as present; README explains where identity,
  ownership, authorization, per-team quota, and audit would enter the architecture.

## Handoff Evidence

- [x] README documents build/run from clean checkout, architecture/data flow, all ten
  assignment discussion areas, debugging signals, and known limitations.
- [x] `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, Make targets, and ADR statuses match
  the implemented system rather than the original plan.
- [x] A 15-minute demo script covers submit, status, ranked results, download,
  metrics/logs, Kubernetes shape, and one deliberate failure.
- [x] Commit history is incremental; each portal commit is focused, passes its
  applicable checks, and has a Conventional Commit subject plus descriptive bullet
  body.
- [x] Final `git status` contains only intentional changes, and the handoff reports
  exact commands/results, assumptions, limitations, and unverified areas.
