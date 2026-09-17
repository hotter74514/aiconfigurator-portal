# Verification Checklist

Record exact commands, versions, inputs, observed outputs, and dates as work is
completed. A checkbox without evidence is not a pass. Commands marked "configure in
Stage 1" describe the intended stable Make target, not a command already verified.

## Reproducibility and Dependency Proof

- [ ] A clean checkout installs only from the committed lockfile and documented
  Linux x86-64 container build.
- [ ] README lists required Docker/kubectl/cluster tools, tested versions, startup
  commands, safe example values, and first-run network/cache behavior.
- [x] The pinned AIConfigurator version completes the documented
  `Qwen/Qwen3-32B-FP8`, 32 × `h200_sxm` SDK smoke run with explicit TTFT/TPOT,
  `top_n`, and `save_dir`.
- [x] Evidence records the SDK result keys/columns, generated artifact tree, runtime,
  peak memory when practical, and SLA-filter behavior.
- [ ] The image and manifest contain no credentials, private data, local paths,
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
- [ ] SIGTERM stops admission/readiness, gives active work the documented grace
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
- [x] One-hour TTL cleanup removes terminal metadata/files; active work is retained;
  startup removes or reconciles documented orphan state.
- [ ] Full/unwritable temporary storage fails the run clearly while live/ready remain
  semantically correct.

## Observability and Resource Behavior

- [x] `/health/live` tests web-process/event-loop health and remains responsive
  during a sweep.
- [x] `/health/ready` tests initialization/admission lifecycle, becomes false during
  shutdown, and does not flap merely because the queue is busy.
- [x] `/metrics` exposes low-cardinality submitted/completed/failed/rejected totals,
  active work, queue depth, and duration without run/model/user labels.
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
  download succeed on an available local cluster.
- [ ] Pod deletion during a run demonstrates the documented loss/`404` behavior
  after restart; no durability claim is made.

## Browser Validation — Playwright MCP Only

- [x] Desktop viewport: submit the documented default, observe queued/running,
  inspect ordered results and estimate warning, and download/inspect the ZIP.
- [ ] Narrow viewport: all form controls, status, result fields, warning, and download
  remain usable; record viewport and screenshot only if useful for evidence.
- [ ] Keyboard-only: labels, focus order, submission, status announcement, result
  navigation, retry, and download are usable.
- [ ] Client and server validation: invalid field and dependency failure each show a
  recoverable message without a browser console error.
- [ ] Polling stops after completed/failed state and does not issue duplicate
  submissions on repeated clicks.
- [ ] If Playwright MCP is unavailable, record the blocker and leave these unchecked;
  do not substitute another browser automation tool.

## Trust and Product Safety

- [ ] User input is mapped to typed SDK arguments and never interpolated into a shell
  command, log format string, artifact path, or rendered unsafe HTML.
- [ ] Generated manifests are never automatically applied and every result/download
  experience says predictions require real benchmark validation.
- [ ] No authentication is represented as present; README explains where identity,
  ownership, authorization, per-team quota, and audit would enter the architecture.

## Handoff Evidence

- [ ] README documents build/run from clean checkout, architecture/data flow, all ten
  assignment discussion areas, debugging signals, and known limitations.
- [ ] `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, Make targets, and ADR statuses match
  the implemented system rather than the original plan.
- [ ] A 15-minute demo script covers submit, status, ranked results, download,
  metrics/logs, Kubernetes shape, and one deliberate failure.
- [ ] Commit history is incremental; each commit is focused, passes its applicable
  checks, and has a Conventional Commit subject plus descriptive bullet body.
- [ ] Final `git status` contains only intentional changes, and the handoff reports
  exact commands/results, assumptions, limitations, and unverified areas.
