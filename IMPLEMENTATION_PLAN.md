# Serving Configuration Portal Implementation Plan

## Plan Status

**ADR-001 and ADR-002 Accepted; Stage 1 is now in progress.** Planning and
read-only discovery are complete. TASK-001 is the current active task.

## Observable Outcome

From a clean checkout, an evaluator can build one Linux x86-64 image, open the
portal, submit the documented Qwen/H200 example, watch it move through queued and
running states, inspect ranked AIConfigurator estimates, and download the exact
deployment artifacts produced by that run. The same image exposes distinct live and
ready probes, Prometheus metrics, and structured logs and can be deployed with the
checked-in Kubernetes manifests.

The acceptance criteria in `docs/project-brief.md` are authoritative. The plan does
not include authentication, durable history, caching, Pareto charts, automatic
deployment, or real-GPU benchmarking.

## Proposed Technical Shape

- Python/FastAPI, server-rendered Jinja2, and native JavaScript keep the application
  and UI in one deployable service.
- A `POST /api/runs` plus polling `GET /api/runs/{id}` API models the long-running
  sweep explicitly.
- One isolated worker process invokes the pinned AIConfigurator Python SDK. The
  portal adapter converts version-specific DataFrames into stable result records.
- One active run plus four queued runs bounds contention; overload is `429` with a
  retry hint.
- In-memory run metadata and a size-limited `emptyDir` retain results for one hour.
- Raw Kubernetes YAML keeps local-cluster deployment inspectable in an interview.

See the Proposed ADRs for rejected alternatives, failure modes, and decision-change
conditions.

## Time Budget and Cut Line

| Stage | Budget | Deliverable | Cut rule |
|---|---:|---|---|
| 1. Prove dependency and scaffold | 1.5 h | Real SDK smoke evidence and testable skeleton | Stop if the real run cannot be reproduced after three distinct attempts |
| 2. Implement bounded run lifecycle | 2.0 h | Async API, worker isolation, status, failures | Required |
| 3. Complete user result/download path | 1.5 h | Form, polling, ranked table, ZIP | Required |
| 4. Add operability and deployment | 2.0 h | Logs, metrics, probes, image, Kubernetes | Required |
| 5. Verify and prepare handoff | 1.5 h | Checks, browser/local-cluster evidence, README/demo | Required |
| Reserve | 1.5 h | Integration fixes and evidence gaps | Do not spend on nice-to-haves until all gates pass |

Total planned time is 8.5 hours plus a 1.5 hour reserve. Optional improvements are
ordered at the end and are outside the committed scope.

## Stage 1: Prove the Dependency and Scaffold

**Goal:** Remove the highest-risk unknown before building around AIConfigurator.

**Prerequisites:** ADR-001 and ADR-002 are Accepted; create a feature branch rather
than working on `main`.

**Work:**

1. Select and pin a released AIConfigurator version only after a Linux x86-64 image
   can install it. Record the image base, Python version, package hashes/lockfile,
   and whether the model config needs first-run network access.
2. In that image, run the assignment smoke case:
   `Qwen/Qwen3-32B-FP8`, 32 GPUs, `h200_sxm`, using explicit TTFT/TPOT and
   `save_dir`. Exercise the documented SDK entry point rather than the shell CLI.
3. Record elapsed time, peak memory when practical, `best_configs` keys/columns,
   SLA behavior, and the generated artifact tree. Confirm which columns map to
   throughput, TTFT, TPOT, mode, and topology.
4. Add the minimal package layout, dependency lock, FastAPI app factory, adapter
   interface, pytest fixture, and configured Ruff/type/test/build Make targets.
5. Add a deterministic fake adapter so most tests never depend on external model
   metadata or a multi-minute sweep.

**Success Criteria:**

- The real pinned SDK returns structured ranked data and files in the container.
- An adapter contract is based on captured evidence, not guessed CSV/stdout fields.
- A minimal app imports and its baseline test passes on the selected Python version.
- `make check` runs real configured commands rather than skip messages.

**Tests / Evidence:**

- Container smoke command and artifact inventory recorded in the task evidence.
- Adapter contract test uses a captured, non-sensitive minimal result fixture.
- `uv run pytest tests/test_app.py` (provisional until Stage 1 configures tooling).
- `make check` and `git diff --check`.

**Status:** Complete.

## Stage 2: Implement the Bounded Run Lifecycle

**Goal:** A client can submit valid work and observe a correct terminal state without
blocking the HTTP request or starving the web process.

**Work:**

1. Write lifecycle and API tests first for validation, `202`, state transitions,
   unknown IDs, dependency failure, timeout, and full-queue rejection.
2. Define typed request/result/error models and a run service that owns state
   transitions. Generate UUIDs server-side; never derive paths from user input.
3. Add a one-process executor, active-count/queue bound, wall-clock timeout, and
   graceful shutdown behavior. Normalize worker exceptions at the process boundary.
4. Invoke `cli_default` with explicit `top_n`, SLA, token-length defaults,
   `strict_sla` behavior confirmed in Stage 1, deployment target, and per-run
   `save_dir`.
5. Ensure invalid/unsupported combinations fail as user-visible run failures or
   validation errors without exposing stack traces.

**Success Criteria:**

- Submission responds before the fake/real worker completes.
- The only legal transitions are queued → running → completed/failed.
- One active plus four queued requests are admitted; the next receives retryable
  `429` and queue size stays bounded.
- A failed/timed-out child does not terminate the API process.

**Tests / Evidence:**

- Unit tests for transition invariants and typed normalization.
- API tests for valid/invalid input, `202`, polling, `404`, `429`, timeout, and
  sanitized failure.
- Probe loop run concurrently with a CPU-bound test worker.
- Narrow test command, then `make check` and `git diff --check`.

**Status:** Complete.

## Stage 3: Complete the Result and Artifact User Path

**Goal:** A browser user can complete every functional must-have without reading
AIConfigurator documentation.

**Work:**

1. Write behavior tests for the form defaults, progress/error states, ranked table,
   estimate warning, and download state rules.
2. Render a single accessible page with model, GPU system, total GPU count, TTFT,
   TPOT, ISL, and OSL. Use a conservative tested example as the default.
3. Submit JSON, poll at the server-advertised two-second interval, stop on terminal
   state, and render normalized rows in rank order.
4. Show throughput, throughput/GPU when available, TTFT, TPOT, serving mode, and
   topology fields verified in Stage 1. Avoid guessing absent values.
5. Stream a ZIP for a completed run only. Add one-hour expiry cleanup and startup
   orphan cleanup. Display that artifacts are estimates requiring benchmark
   validation before production.

**Success Criteria:**

- The browser flow covers submit → progress → results → ZIP without manual URL edits.
- Failed/unsupported runs explain the next action without leaking internal paths.
- ZIP content is scoped to the run and contains generated deployment artifacts.
- Cleanup removes both metadata and files at expiry.

**Tests / Evidence:**

- API tests for early (`409`), successful, unknown/expired (`404`), and isolated ZIP
  downloads.
- Tests for cleanup and path-containment rules.
- Playwright MCP scenarios are executed in Stage 5; no alternate browser driver is
  substituted.
- Narrow test command, then `make check` and `git diff --check`.

**Status:** Complete.

## Stage 4: Add Operability, Container, and Kubernetes Delivery

**Goal:** Another engineer can run and operate the portal, and CPU contention is
visible and bounded.

**Work:**

1. Emit JSON lifecycle logs with timestamp, severity, event, run ID, status,
   duration, and safe error category. Do not log artifact bodies or high-cardinality
   values as metric labels.
2. Expose low-cardinality Prometheus metrics for submitted/completed/failed/rejected
   runs, active runs, queue depth, and run duration. Add HTTP metrics only if they
   remain simple and bounded.
3. Implement liveness (process/event loop) and readiness (initialized, accepting,
   not shutting down) and test that being busy alone does not make the pod unready.
4. Build a multi-stage, non-root Linux x86-64 image with pinned dependencies and no
   build tools in the runtime layer. Add a healthcheck for local Docker use.
5. Add Namespace-agnostic Deployment and Service YAML with one replica, `Recreate`,
   startup/live/ready probes, `emptyDir` size limit, read-only root filesystem where
   compatible, dropped capabilities, and measured resource values. Start the
   measurement with two CPU and 4 GiB memory requests/limits; adjust from evidence.
6. Set a termination grace period and stop accepting work on SIGTERM. Document that
   work exceeding the grace period is lost rather than pretending it is durable.

**Success Criteria:**

- Logs correlate a run without exposing contents, and metrics answer load,
  saturation, latency, and failure questions.
- Probes remain responsive during the real smoke sweep under the declared cgroup
  limits.
- Container runs as non-root and writes only to the designated temporary paths.
- Kubernetes resources validate client-side and deploy on the available local
  cluster; absence of a cluster is recorded rather than hidden.

**Tests / Evidence:**

- Tests for probe semantics, metric increments, structured log fields, shutdown,
  and disk/write failure.
- `docker build --platform linux/amd64 ...` and real container smoke run.
- `kubectl apply --dry-run=client -f deploy/`.
- Local-cluster rollout, probe, metrics, run, and download checks when a cluster is
  available.
- `make check`, configured build/integration targets, and `git diff --check`.

**Status:** Not Started.

## Stage 5: Verify and Prepare Handoff

**Goal:** Produce reproducible evidence and an interview-ready 15-minute demo.

**Work:**

1. Execute every item in `docs/verification-checklist.md`, recording exact commands,
   versions, inputs, durations, and observed results.
2. Use Playwright MCP for the success flow, invalid input, failed dependency,
   keyboard flow, narrow viewport, polling state, and file download.
3. From a clean checkout/build cache where practical, repeat build → run → submit →
   results → download. Inspect the ZIP and generated Kubernetes YAML.
4. Replace the harness README with setup/run instructions, architecture diagram,
   decisions answering assignment section 6, operational debugging guide, and known
   limitations. Make clear that generated output requires real benchmarking.
5. Reconcile `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, Make targets, ADR status,
   and verification evidence with actual behavior. Review the diff for secrets,
   generated files, and unrelated edits.
6. Prepare a short demo script and the likely extension discussion: durable queue,
   Kubernetes Jobs, object storage, multi-user authorization/quotas, caching key and
   version invalidation, and benchmark feedback loop.

**Success Criteria:**

- Clean-checkout instructions are actually executed and reproducible.
- All must-have acceptance criteria have automated or recorded behavior evidence.
- Known limitations describe restart loss, single replica/concurrency, lack of auth,
  TTL, estimation uncertainty, and any unverified local-cluster behavior.
- `make check`, `make integration`, `make build`, and `git diff --check` pass when
  configured; no skipped configured gate is represented as passing.

**Tests / Evidence:** See `docs/verification-checklist.md`.

**Status:** Not Started.

## Test Matrix

| Boundary | Happy path | Important failure |
|---|---|---|
| Request validation | Tested defaults and supported-shaped request | Missing/invalid numbers, unknown system, oversized strings |
| Admission | One active and bounded queue | Queue full returns `429` and retry hint |
| Worker | Structured rows and artifacts returned | SDK exception, timeout, process exit, no feasible config |
| Lifecycle | queued → running → completed | queued/running → failed; illegal transitions rejected |
| Results | Rank and required metrics are stable | Unknown/expired ID; missing optional column |
| Download | Correct run ZIP and safe filename | Incomplete `409`, unknown `404`, path isolation, disk failure |
| Cleanup | Terminal run deleted after TTL | Active run is never prematurely deleted |
| Operations | Logs/metrics/probes during load | Shutdown, saturation, CPU pressure, storage pressure |
| Packaging | Clean Linux x86-64 build and smoke | Missing dependency/data/network is actionable |
| Browser | Submit, poll, results, download | Invalid form and failed run are recoverable |

## Risks, Assumptions, Dependencies, and Rollback

- The plan assumes the documented `cli_default` Python API and `best_configs` work in
  a released Linux x86-64 package. Stage 1 is a stop/go gate, not a formality.
- The exact SDK fields, package version, Python version, supported systems, and
  resource limits are deliberately not frozen until measured.
- The macOS host currently has `uv 0.11.21`, Python 3.14.5, Docker CLI 29.4.0,
  kubectl 1.37.0, Node 26.8.1, and npx 11.19.0. `kind` is absent and the configured
  Docker/OrbStack daemon was not running during planning; local-cluster execution is
  therefore not yet verified.
- Each stage is a focused commit with real newlines and a descriptive body. If a
  stage fails, revert that stage's commit; do not weaken tests or probes.
- If the SDK is unusable after three materially different attempts, stop and report
  the commands/errors. A CLI subprocess with machine-readable generated CSV is the
  fallback only after its exact contract is verified and ADR-001 is revised.
- If two CPU/4 GiB is insufficient, adjust from recorded measurements. If probes are
  delayed, first reduce worker thread parallelism or reserve more CPU; do not make
  probe thresholds mask starvation.

## Optional Work After All Gates Pass

1. Pareto frontier chart using already-returned normalized rows.
2. Clear aggregated-versus-disaggregated comparison summary.
3. Deterministic cache keyed by canonical request, AIConfigurator version, profile
   data/version, backend/generator version, and portal normalization schema.
4. Durable history and user ownership only after replacing local state/storage.

## References

- [AIConfigurator README](https://github.com/ai-dynamo/aiconfigurator/blob/main/README.md)
- [AIConfigurator CLI User Guide](https://github.com/ai-dynamo/aiconfigurator/blob/main/docs/cli_user_guide.md)
- [AIConfigurator Support Matrix](https://ai-dynamo.github.io/aiconfigurator/support-matrix/)
