# Serving Configuration Portal Implementation Plan

## Plan Status

**ADR-001 through ADR-007 Accepted; Stages 1–5 are complete.** Planning,
implementation, operations, and handoff evidence are recorded. The repository owner
confirmed TASK-006 validation has no known issues. The optional extension in Stages
6–10 is now available, with each stage still independently gated by its corresponding
accepted ADR.

## Observable Outcome

From a clean checkout, an evaluator can build one Linux x86-64 image, open the
portal, submit the documented Qwen/H200 example, watch it move through queued and
running states, inspect ranked AIConfigurator estimates, and download the exact
deployment artifacts produced by that run. The same image exposes distinct live and
ready probes, Prometheus metrics, and structured logs and can be deployed with the
checked-in Kubernetes manifests.

The acceptance criteria in `docs/project-brief.md` are authoritative for the
baseline. The baseline does not include authentication, durable history, caching,
Pareto charts, automatic deployment, or real-GPU benchmarking. The proposed
optional extension below adds deliberately ephemeral versions of visualization,
comparison, caching, history, and multi-user awareness without claiming durable
storage, identity, authorization, or isolation.

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

See the accepted ADRs for rejected alternatives, failure modes, and decision-change
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

**Status:** Complete. Container, probes, metrics, logs, manifest evidence, and a
successful Minikube rollout with a real run/download are recorded in
`docs/evidence/task-005-operations.md`.

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

**Status:** Complete. Automated checks, container smoke, Playwright MCP browser flow,
and live-cluster validation are recorded; the repository owner confirmed the handoff
has no known issues.

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
  kubectl 1.37.0, Node 26.8.1, and npx 11.19.0. The OrbStack daemon is available
  for image builds. Minikube v1.39.0 runs an arm64 Kubernetes v1.37.0 node with
  x86_64 emulation; the Linux amd64 image must be imported into containerd because
  `minikube image load` rejects the cross-architecture image.
- Each stage is a focused commit with real newlines and a descriptive body. If a
  stage fails, revert that stage's commit; do not weaken tests or probes.
- If the SDK is unusable after three materially different attempts, stop and report
  the commands/errors. A CLI subprocess with machine-readable generated CSV is the
  fallback only after its exact contract is verified and ADR-001 is revised.
- If two CPU/4 GiB is insufficient, adjust from recorded measurements. If probes are
  delayed, first reduce worker thread parallelism or reserve more CPU; do not make
  probe thresholds mask starvation.

## Optional Extension: Results Insight and Ephemeral Convenience

### Extension Outcome and Cut Line

After the baseline delivery gate passes, a user can understand the trade-off between
aggregated and disaggregated serving, inspect the full Pareto visualization produced
by the same AIConfigurator run, avoid recomputation for an identical recent request,
return to recent runs from the same browser, and see anonymous service pressure from
other users.

This extension intentionally does **not** add authentication, authorization,
cross-device history, durable cache entries, or restart survival. Those capabilities
require a different storage and identity boundary. ADR-003 through ADR-007 separate
the five feature decisions so the owner can accept or reject each independently.

The cut line is strict:

1. Finish TASK-006 and the unchecked baseline verification items that are applicable.
2. Review each ADR separately; acceptance of one does not imply acceptance
   of any other optional feature.
3. Implement visualization and comparison first because they add the most direct
   user value without changing execution or storage ownership.
4. Implement cache, history, and awareness only if time remains; each is independently
   removable. Do not replace the local process/storage model for a nice-to-have.

| Extension stage | Expected effort | Deliverable | Required decision |
|---|---:|---|---|
| 6. Expose the Pareto frontier | 1.5–2.5 h | Verified run-scoped Pareto asset | Accepted ADR-003 |
| 7. Compare agg and disagg | 1–2 h | Server-owned comparison summary and UI | Accepted ADR-004 |
| 8. Reuse identical completed results | 2–3 h | Bounded deterministic in-process cache | Accepted ADR-005 |
| 9. Restore recent browser runs | 1.5–2 h | Browser-local history | Accepted ADR-006 |
| 10. Show shared service pressure | 1–1.5 h | Anonymous aggregate capacity awareness | Accepted ADR-007 |

The full extension is approximately 7–11 hours. With only 2–4 hours available,
ship Stages 6 and/or 7 with their verification; do not start persistence or identity
work. Each stage includes its own documentation and completion-gate checks.

### Stage 6: Expose the Pareto Frontier

**Goal:** Show the complete frontier produced by the same run without reconstructing
it from incomplete top-N rows.

**Prerequisites:** TASK-006 complete and ADR-003 Accepted.

**Work:**

1. In the pinned Linux image, inventory every `pareto_frontier.png`: count, relative
   path, parent mode, dimensions, and whether it reflects the full sweep or `top_n`.
2. Extend the result contract with whitelisted visualization metadata discovered
   beneath the server-generated run root.
3. Add a completed-run visualization endpoint keyed by a server-issued ID. Enforce
   status, path containment, allowlisted PNG media type, and expiry semantics.
4. Render captions, alternative text, scope/axis notes, the benchmark warning, and
   the existing table as the exact-value fallback.

**Success Criteria:**

- The displayed image is verified dependency output from that same run.
- Unsafe, missing, ambiguous, or non-PNG assets are never served or mislabeled.
- No frontend chart dependency or top-N frontier recomputation is introduced.

**Tests / Evidence:** Adapter discovery; successful image response; queued `409`;
unknown/expired `404`; missing file; unsupported media; symlink/path escape; and
Playwright MCP desktop, narrow, keyboard, caption, fallback, and warning scenarios.
Then run `make check` and `git diff --check`.

**Status:** Not Started.

### Stage 7: Compare Aggregated and Disaggregated Results

**Goal:** Explain cross-mode trade-offs with one stable, testable comparison contract.

**Prerequisites:** TASK-006 complete and ADR-004 Accepted. Stage 6 is optional.

**Work:**

1. Verify that rank 1 is the best row independently within both `agg` and `disagg`.
2. Add a portal-owned optional comparison block derived from those two rows.
3. Return absolute throughput, TTFT, TPOT, GPU count, signed percentage deltas,
   documented rounding, and explicit unavailable reasons.
4. Render side-by-side values without declaring a universal winner; preserve the raw
   ranked table and benchmark warning.

**Success Criteria:**

- Two-mode results show correct values and signed deltas.
- Missing modes, missing values, and zero baselines remain explicit and usable.
- Comparison domain logic is owned and tested by the server rather than duplicated
  in browser code.

**Tests / Evidence:** Fixtures for both modes and missing cases; tests for row
selection, units, signs, zero division, rounding, and unavailable reasons; Playwright
MCP desktop, narrow, and keyboard flows; `make check` and `git diff --check`.

**Status:** Not Started.

### Stage 8: Add a Bounded Deterministic Result Cache

**Goal:** An identical recent request can complete without another CPU-heavy sweep,
while preserving a fresh run ID and the existing API lifecycle contract.

**Prerequisites:** TASK-006 complete and ADR-005 Accepted. Stages 6 and 7 are
optional; the cached bundle includes only result fields that are implemented.

**Work:**

1. Write cache behavior tests before implementation. Define one canonical JSON
   serialization for every `RunRequest` field and hash it with an explicit dependency
   and normalization version namespace.
2. Cache only successful completed bundles: normalized rows, visualization bytes,
   source/version metadata, and the generated artifact ZIP. Never cache failures,
   queued/running work, or an entry with unknown version inputs.
3. On a hit, create a new opaque run ID and a completed record; do not reveal or reuse
   another caller's run ID. Keep `POST /api/runs` at `202` so clients retain one
   contract, even when the first poll observes `completed`.
4. Bound the process-local cache by TTL, entry count, and total bytes with predictable
   least-recently-used eviction. Clear it on restart. Avoid duplicate in-flight
   coalescing in this increment.
5. Add low-cardinality hit, miss, and eviction metrics. Never log raw cache keys,
   model names, request payloads, or user-derived labels.

**Success Criteria:**

- Two identical completed requests execute the worker once and return distinct run
  IDs with equivalent results, visualizations, and downloadable ZIP content.
- Any request-field or namespace-version change is a miss.
- Failed and in-flight requests never produce hits.
- TTL, LRU count, and byte limits keep memory bounded, and restart loss is explicit.

**Tests / Evidence:**

- Unit tests for canonicalization, version invalidation, TTL, byte/count eviction,
  misses, and no failure caching.
- Run-manager/API concurrency tests for distinct IDs, one worker execution after a
  completed hit, artifact equivalence, and cache isolation from run expiry.
- Metrics assertions with no high-cardinality labels.
- Container check showing a hit in one process and a miss after restart.
- Narrow checks, then `make check`, `make integration`, and `git diff --check`.

**Status:** Not Started.

### Stage 9: Add Browser-Local Run History

**Goal:** A user can revisit recent submissions known to the same browser without a
server-wide enumeration endpoint.

**Prerequisites:** TASK-006 complete and ADR-006 Accepted. Other optional stages are
not required.

**Work:**

1. Store a capped recent-run index in browser `localStorage`: run ID, submitted-at
   time, and a concise request summary. Treat it as untrusted display data and render
   only through DOM text properties.
2. On page load, re-fetch each stored opaque run ID from the existing status API,
   update its state, and prune malformed, unknown, or expired entries. Selecting an
   available entry restores its status/results without resubmission.
3. Cap history at 20 entries and provide a browser-only clear action. Do not add a
   server-side list-runs endpoint, session cookie, or claim of durable history.

**Success Criteria:**

- Refreshing the same browser restores up to 20 known runs while valid; clearing site
  data, server restart, or one-hour expiry has the documented loss behavior.
- History cannot enumerate other users' runs and uses no unsafe HTML insertion.
- UI and README state plainly that this is convenience history, not authentication,
  authorization, privacy isolation, or auditing.

**Tests / Evidence:**

- UI logic tests where practical for cap/prune/order and malformed local storage.
- Playwright MCP scenarios for refresh restore, expired pruning, clear history,
  two browser contexts with separate local history, narrow viewport, and keyboard
  access.
- Narrow checks, then `make check` and `git diff --check`.

**Status:** Not Started.

### Stage 10: Add Anonymous Multi-User Capacity Awareness

**Goal:** Show shared queue pressure without introducing identity-like semantics or
exposing another caller's run details.

**Prerequisites:** TASK-006 complete and ADR-007 Accepted. Other optional stages are
not required.

**Work:**

1. Add a read-only endpoint returning only active count, queued count, configured
   capacities, and whether admission is open.
2. Render a neutral shared-pressure banner and explain that it is informational and
   the portal has no accounts, ownership, reservation, fairness, or quotas.
3. Poll at no more than the existing status interval and only while the page is
   visible. Expose no run IDs, model inputs, timestamps, IPs, cookies, or user labels.
4. Record endpoint latency during a real sweep and update the applicable verification
   checklist, evidence, architecture, README, roadmap, and task status.

**Success Criteria:**

- Idle, active, queued, saturated, and shutdown states have bounded payloads.
- Two browser contexts see the same aggregate pressure without sharing run details.
- Capacity checks remain responsive during CPU work and do not reserve a slot.
- Documentation never represents awareness as authentication or isolation.

**Tests / Evidence:**

- API tests for every capacity state and exact allowlisted response fields.
- Playwright MCP two-context, page-visibility, narrow, and keyboard scenarios.
- Probe/capacity latency observation during a real sweep.
- Applicable configured checks, `make check`, and `git diff --check`.

**Status:** Not Started.

### Extension Risks, Assumptions, and Rollback

- The plan assumes AIConfigurator's generated PNG is a trustworthy full-frontier
  artifact. If evidence disproves that assumption, ADR-003 requires omission until a
  complete structured frontier contract exists.
- Rank 1 is assumed to be meaningful independently per mode; it must not be used for
  comparison until verified.
- Cached artifacts are safe to reuse only for an exact canonical request and version
  namespace. Any ambiguity is a cache miss.
- Browser-local history can expose request summaries to anyone using the same browser
  profile. Keep summaries minimal, document the behavior, and provide clear-history.
- Anonymous capacity is intentionally not identity. Real ownership, private history,
  per-user quotas, audit, cross-device access, or multi-replica operation triggers a
  new Accepted ADR and durable storage design.
- Each optional stage owns its tests, documentation, and focused commit and can be
  accepted, implemented, or reverted independently. An incomplete stage remains
  unshipped rather than weakening its gate.

## References

- [AIConfigurator README](https://github.com/ai-dynamo/aiconfigurator/blob/main/README.md)
- [AIConfigurator CLI User Guide](https://github.com/ai-dynamo/aiconfigurator/blob/main/docs/cli_user_guide.md)
- [AIConfigurator Support Matrix](https://ai-dynamo.github.io/aiconfigurator/support-matrix/)
