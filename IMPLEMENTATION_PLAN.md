# Serving Configuration Portal Implementation Plan

## Plan Status

**ADR-001 through ADR-009 Accepted; ADR-010 is superseded by Proposed ADR-011.
Stages 1–25 are complete; Stage 26 requires correction.**
Planning, implementation,
operations, and handoff evidence are recorded for completed work. The repository
owner confirmed TASK-006 validation has no known issues. The optional extension in
Stages 6–10 passed its final automated, container, cluster, and browser gates; the
project-scoped Playwright MCP server uses an isolated profile to avoid the observed
Chrome download crash.

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

**Status:** Complete. The pinned SDK artifact semantics, contained visualization
endpoint, accessible metadata/fallback, API security tests, and Playwright MCP
browser evidence are recorded in `docs/evidence/task-007-pareto-frontier.md`.

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

**Status:** Complete. Domain tests define rank-1 selection, signed deltas,
rounding, and unavailable states; automated checks and Playwright MCP desktop,
narrow, and keyboard validation are recorded in the task evidence.

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

**Status:** Complete. Canonicalization, namespace invalidation, bounded eviction,
TTL, failure/in-flight exclusion, metrics, artifact equivalence, and restart-loss
evidence are recorded in `docs/evidence/task-009-bounded-result-cache.md`.

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

**Status:** Complete. Client contract tests and Playwright MCP browser evidence cover
the cap, ordering, malformed/expired/unknown pruning, refresh restore, clear action,
browser isolation, narrow layout, and keyboard access.

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

**Status:** Complete. API/UI implementation, automated checks, Playwright MCP browser
validation, and pinned-container real-sweep latency evidence are recorded.

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

## UI Refresh Extension: Precision Planning Workspace

### Direction and Boundaries

Refresh the portal as a calm, high-density engineering workspace rather than a
generic marketing dashboard. The page should make the primary sequence immediately
clear: define a workload, observe the run, compare trade-offs, then download the
generated artifacts. Visual polish must improve comprehension without changing the
run API, storage, worker, cache, or security boundaries.

Use the framework-agnostic `frontend-design` skill as the art-direction and
implementation guide. Use `web-design-guidelines` as a separate post-implementation
audit for interaction, accessibility, responsive behavior, and copy. Record the
exact upstream source and commit used before implementation; do not silently update
a skill midway through the work. The internal marketplace candidates are not the
default: `fedex-dev` assumes React/Tonic migration concerns that this portal does not
have, while a full `ux-atelier` adoption would add a prototype/handoff workflow that
is larger than this single-page refresh needs.

Keep FastAPI, Jinja2, and native JavaScript. Add no frontend framework, component
library, package manager, build pipeline, analytics, external font CDN, or runtime
network dependency. A proposal that needs any of those changes crosses the current
architecture boundary and must stop for owner review and, if material, a Proposed
ADR. Preserve every API contract, DOM hook used by `portal.mjs`, estimate warning,
history limitation, and anonymous-capacity limitation.

The implementation begins only after TASK-012 reconciles the existing optional
feature evidence. Estimated effort is 4–6 hours plus review time.

### Stage 11: Baseline the Existing Experience and Lock the Design Brief

**Goal:** Establish an evidence-backed visual direction and regression baseline
before changing markup or styles.

**Work:**

1. Install or load the selected `frontend-design` skill in personal Codex scope,
   pin its upstream revision in task evidence, and confirm that it requires no
   shipped runtime dependency.
2. Use Playwright MCP to capture the current page at 1440×900 and 390×844 for ready,
   running, completed, failed, saturated, empty-history, and populated-history
   states. Record keyboard order and obvious overflow or hierarchy problems.
3. Produce a one-page design brief for a “precision planning workspace”: restrained
   neutral surfaces, one clear action color, tabular/monospace treatment for metrics,
   strong status semantics, and motion limited to state feedback.
4. Map the existing DOM IDs and JavaScript behaviors that must remain stable. Define
   a CSS token set for color, type, spacing, radius, shadow, focus, and state colors.

**Success Criteria:** The before-state evidence is reproducible; the brief identifies
the primary task, information hierarchy, responsive strategy, and complete UI-state
matrix; no product or architecture requirement is inferred from the design skill.

**Tests / Evidence:** Playwright MCP screenshots and keyboard notes, existing narrow
tests, `make check`, and `git diff --check`.

**Status:** Complete. Baseline screenshots, keyboard notes, stable DOM hook inventory,
and the pinned design brief are recorded in `docs/evidence/task-013-design-brief.md`.

### Stage 12: Build the Visual Foundation and Responsive Shell

**Goal:** Give the page an intentional, accessible visual system without changing
application behavior.

**Work:**

1. Add a dedicated static stylesheet and link it from the Jinja template. Define
   semantic CSS custom properties rather than scattering literal colors and sizes.
2. Restructure presentation markup into a responsive workspace: concise product
   header, prominent estimate warning, clear configuration panel, compact run-status
   and shared-capacity region, and a results workspace that receives the most space.
3. Style native inputs, select, buttons, links, focus rings, disabled states, tables,
   and cards consistently. Keep native semantics and visible labels; use decoration
   only when it does not become the sole carrier of meaning.
4. Use one-column flow on narrow viewports and a measured desktop grid. Avoid
   horizontal page overflow; contain wide comparison and results tables locally.
5. Respect `prefers-reduced-motion`, browser zoom, forced colors where practical,
   and mobile target/input sizing. Do not hide content solely to simplify layout.

**Success Criteria:** The ready state has a clear first action and readable hierarchy
at 320 px through desktop widths; all controls have visible hover/focus/disabled
states; the page loads with no new runtime network request or frontend dependency.

**Tests / Evidence:** Template/static-asset tests first; Playwright MCP desktop,
390 px, 320 px, 200% zoom, keyboard, reduced-motion, and no-horizontal-page-overflow
checks; then `make check` and `git diff --check`.

**Status:** Complete. The tokenized stylesheet, semantic responsive shell, reduced-motion
handling, and static delivery checks are implemented and verified in TASK-013 evidence.

### Stage 13: Polish Run, Result, Comparison, and History States

**Goal:** Make every asynchronous state and decision surface easy to scan without
changing lifecycle semantics.

**Work:**

1. Add presentation-only status classes or `data-*` state attributes in
   `portal.mjs`; keep polling intervals, error handling, history behavior, and API
   payloads unchanged.
2. Render queued/running/completed/failed and capacity states with consistent text,
   iconography, color, and live-region behavior. Preserve actionable sanitized
   errors and do not rely on color alone.
3. Improve comparison and ranked-result hierarchy with metric cards or grouped
   headings, aligned numerals, table captions/header scopes, explicit units, and a
   prominent artifact-download action. Preserve exact values and the no-universal-
   winner and benchmark warnings.
4. Make recent runs compact and scannable while retaining all browser-only,
   expiry, shared-profile, and no-ownership caveats.
5. Cover visualization available, loading, and image-error fallback states without
   replacing the exact-value table.

**Success Criteria:** Every state in the Stage 11 matrix is visually distinct,
keyboard reachable, understandable without color, and consistent on narrow and
desktop layouts; no API, caching, history, or security behavior changes.

**Tests / Evidence:** Add deterministic client tests for any extracted state-to-view
logic and update server template assertions where wording changes. Use Playwright MCP
for the full submit → progress → result → download path plus failure, saturation,
history restore/clear, visualization fallback, comparison unavailable, and two-
context capacity scenarios. Run narrow checks, then `make check` and
`git diff --check`.

**Status:** Complete. Presentation-only state attributes and polished result, comparison,
visualization, history, capacity, failure, and download states are verified with
Playwright MCP fixtures and automated checks.

### Stage 14: Audit, Regress, and Hand Off the Refresh

**Goal:** Prove that visual polish did not weaken function, accessibility,
operability, or documentation.

**Work:**

1. Run the `web-design-guidelines` skill against the changed template, stylesheet,
   and client script. Resolve applicable findings or record a concrete rationale.
2. Compare before/after Playwright MCP captures at identical viewports and states.
   Review hierarchy, density, contrast, focus visibility, overflow, motion, loading,
   empty, and error behavior.
3. Execute the complete repository completion gate and the behavior-level path in
   `docs/verification-checklist.md`, including the real container flow where the UI
   consumes real normalized results.
4. Record changed files, exact commands/results, skill source revisions, known
   limitations, and rollback notes in `docs/evidence/task-013-ui-refresh.md`. Update
   README screenshots or UI descriptions only from observed final behavior.

**Success Criteria:** Applicable formatter, lint, type, unit, client, integration,
build, Playwright MCP, `make check`, and `git diff --check` gates pass; functional
behavior and warnings remain intact; git status contains only intentional changes.

**Tests / Evidence:** The complete configured gate, browser state matrix, container
smoke, before/after evidence, source-revision record, and final self-review.

**Status:** Complete. The pinned guideline audit, browser matrix, repository checks,
and handoff evidence are recorded in `docs/evidence/task-013-ui-refresh.md`.

### UI Refresh Risks and Rollback

- A visually ambitious skill can overproduce motion, decoration, or marketing-style
  layouts. The engineering-workspace brief, reduced-motion gate, and state matrix
  constrain that tendency.
- Copy simplification can accidentally weaken required estimate, privacy, capacity,
  or retention disclosures. Treat those messages as acceptance criteria, not visual
  clutter.
- Template restructuring can break JavaScript ID hooks or live regions. Inventory
  those hooks first and keep behavior changes in separately tested client helpers.
- Wide metric tables remain legitimate dense data. Preserve exact-value tables and
  use contained scrolling instead of collapsing or hiding decision data.
- Each stage is a focused, reversible commit. Revert the stage if its visual gains
  cannot pass the same functional and accessibility checks as the baseline.

## OpenTelemetry and Alloy Extension

Implement Accepted ADR-008 as TASK-014. Keep application telemetry explicit and
testable: traces use OTLP, logs remain JSON on stdout with injected trace context,
and OpenTelemetry metrics preserve the Prometheus `/metrics` pull contract. Alloy
routes the signals to Tempo, Loki, and Prometheus, while provisioned Grafana data
sources provide bidirectional trace/log navigation.

### Stage 15: Lock the Telemetry Contract and Test Seams

**Goal:** Turn ADR-008 into executable signal, propagation, cardinality, and failure
contracts before adding runtime dependencies.

**Work:**

1. Inventory the existing log fields and metric names that must remain compatible.
2. Define resource attributes, span names, safe run attributes, metric instruments,
   excluded probe routes, and environment configuration.
3. Define injectable tracer, meter, exporter, and clock seams for deterministic
   tests without a live backend.
4. Specify the W3C carrier stored with a run and the expected HTTP, queue, worker,
   completion, failure, timeout, rejection, and cache-hit relationships.

**Success Criteria:** The contract identifies every emitted field and attribute,
contains no request bodies, artifacts, credentials, baggage, or high-cardinality
metric/Loki labels, and can be tested without Tempo, Loki, or Prometheus.

**Tests / Evidence:** Contract-focused unit tests written first; dependency-resolution
record; narrow test command; `make check`; `git diff --check`.

**Status:** Complete.

### Stage 16: Instrument the Web Process and Preserve Metrics

**Goal:** FastAPI requests emit spans and standard HTTP metrics, portal metrics use
the OpenTelemetry API, and JSON logs contain valid active trace context.

**Work:**

1. Add compatible, locked OpenTelemetry SDK, OTLP, Prometheus, FastAPI, and logging
   packages.
2. Add an explicit telemetry bootstrap with stable resource attributes, bounded
   batch export, disabled mode, dependency injection, force-flush, and shutdown.
3. Instrument each app instance exactly once and exclude live, ready, and metrics
   endpoints from tracing.
4. Extend the JSON formatter with conditional `trace_id`, `span_id`, sampled state,
   and service identity while preserving safe lifecycle fields.
5. Replace custom metric instruments with OpenTelemetry counters, observable gauges,
   and histograms while keeping the required `/metrics` names and semantics.

**Success Criteria:** A request produces one server span; logs inside it contain the
same valid trace and span IDs; disabled/exporter-failure modes do not affect the HTTP
result; existing operational metrics remain queryable without forbidden labels.

**Tests / Evidence:** In-memory span/metric tests; JSON log tests; `/metrics`
compatibility and cardinality assertions; app-factory duplication and lifecycle
tests; narrow checks followed by `make check` and `git diff --check`.

**Status:** Complete.

### Stage 17: Propagate Context through the Run and Worker Boundary

**Goal:** One trace remains causally connected across admission, queue delay,
callback threads, and the isolated AIConfigurator child process.

**Work:**

1. Inject the current W3C Trace Context into a plain string carrier at submission
   and retain it with the run record.
2. Reconstruct context explicitly for start, completion, timeout, and failure work;
   do not rely on callback-thread ambient context.
3. Use an explicit `spawn` process context, initialize child telemetry independently,
   extract the carrier, and wrap AIConfigurator in `portal.run.execute`.
4. Correlate accepted, started, completed, failed, timed-out, rejected, and cache-hit
   logs without changing run API or polling semantics.
5. Re-measure real worker startup, runtime, memory, probe responsiveness, and
   graceful shutdown under the container resource limit.

**Success Criteria:** A known incoming `traceparent` yields the same trace ID in the
HTTP, queued lifecycle, and worker spans and logs, including when work begins after
the HTTP response; propagation does not leak between runs.

**Tests / Evidence:** Thread-executor unit coverage plus a real spawned-process test
against a local OTLP receiver; success, queue, cache, rejection, dependency failure,
timeout, and shutdown cases; real AIConfigurator container observation.

**Status:** Complete. Thread-executor, deterministic, spawned-worker, and real
Minikube OTLP/Tempo propagation evidence are recorded.

### Stage 18: Configure Alloy and Grafana Correlation

**Goal:** Deliver each signal to its backend and provision deterministic two-way
navigation between Tempo traces and Loki logs.

**Work:**

1. Add bounded Alloy OTLP trace reception and Tempo export with memory limiting,
   batching, retry, and deployment-supplied backend configuration.
2. Collect only selected portal pod logs, parse JSON, retain `service_name` as a
   low-cardinality label, and attach trace/span IDs as structured metadata before
   writing to Loki.
3. Discover and scrape portal `/metrics`, apply a low-cardinality label policy, and
   forward to the configured Prometheus-compatible destination.
4. Provision stable Grafana UIDs `tempo`, `loki`, and `prometheus`; configure Tempo
   `tracesToLogsV2` and the Loki `trace_id` derived internal link.
5. Keep endpoint, tenant, TLS, and credential values outside committed configuration
   and validate the Alloy and Kubernetes artifacts before deployment.

**Success Criteria:** Tempo contains application and worker spans; Loki contains
JSON lifecycle logs with searchable structured trace metadata but no trace-ID stream
label; Prometheus contains the required metrics; provisioned Grafana data sources
resolve one another by stable UID.

**Tests / Evidence:** Alloy formatting/config validation, Kubernetes client-side dry
run, backend API queries using one known trace ID, label/cardinality inspection, and
credential/generated-file review.

**Status:** Complete. Alloy log delivery, OTLP/Tempo delivery, Prometheus scrape,
and Grafana datasource correlation were verified in the existing Minikube stack.

### Stage 19: Prove Failure Isolation and Bidirectional Navigation

**Goal:** Demonstrate the complete operator workflow and hand off reproducible
evidence without weakening the portal's functional path.

**Work:**

1. Submit a known `traceparent`, locate the complete trace in Tempo, and confirm its
   corresponding web and worker logs and Prometheus metrics.
2. With Playwright MCP, select **Logs for this span** in Tempo and confirm the Loki
   results use the same trace ID; then select **View Trace** from a log and confirm
   the exact original Tempo trace opens.
3. Test absent, malformed, unsampled, failed, and delayed-ingestion cases without
   broken links or misleading claims.
4. Stop Alloy and each backend in turn and confirm portal traffic, probes, local
   stdout logging, shutdown, memory, and exporter queues remain bounded.
5. Reconcile README, architecture, roadmap, task, checklist, and evidence with the
   observed implementation and limitations.

**Success Criteria:** The two Grafana navigation directions work for the same real
run; telemetry outages do not fail business behavior; every applicable configured,
container, browser, and Kubernetes gate passes; only intentional files remain.

**Tests / Evidence:** Record the trace ID, Tempo/LogQL/PromQL queries, Playwright MCP
navigation observations, outage results, real container flow, full `make check`,
image build, integration tests, manifest validation, and `git diff --check` in
`docs/evidence/task-014-opentelemetry-alloy.md`.

**Status:** Complete. Backend correlation, visible bidirectional Grafana navigation,
outage isolation, bounded resource behavior, graceful shutdown, recovery, and
negative propagation cases are verified.

### Stage 20: Add Portal-Owned Trade-off Surface

**Goal:** Render a responsive, accessible Pareto trade-off surface from the
complete SDK-provided `pareto_fronts` frames while retaining the verified SDK PNG
and exact ranked table as fallback evidence.

**Work:**

1. Normalize finite latency and cluster-throughput points from every complete
   serving-mode frontier and classify cross-mode dominance without using top-N
   rows; reject missing, malformed, or unbounded source frames.
2. Add a versioned JSON payload and deterministic native SVG renderer with axis
   direction labels, frontier connector, legend, point descriptions, and a
   text summary of the frontier.
3. Keep the dependency-generated PNG endpoint and ranked table available when
   the portal-owned surface is absent or unavailable; preserve cache behavior.
4. Verify deterministic fixtures, API serialization, desktop/narrow Playwright
   rendering, keyboard focus, and configured repository checks.

**Success Criteria:** Completed runs expose a bounded `tradeoff_surface` payload;
the page renders blue frontier and slate dominated candidates from the same full
SDK sweep; latency is explicitly minimized, throughput maximized, exact values
remain available in the table, and malformed source data falls back safely.

**Tests / Evidence:** Trade-off normalization unit tests, application payload and
cache tests, `make check`, image build, and Playwright MCP desktop/narrow checks
recorded in the task evidence.

**Status:** Complete. The accepted contract, deterministic normalization, native
SVG/browser rendering, fallback evidence, real SDK source check, and configured
repository/browser gates are recorded in `docs/evidence/task-015-tradeoff-surface.md`.

### Stage 21: Lock the Portal Status Dashboard Contract

**Goal:** Define a testable operator view from the portal's existing low-cardinality
Prometheus metrics without changing application instrumentation.

**Success Criteria:** Tests require a stable dashboard UID, the provisioned
`prometheus` datasource, an instance selector, and panels covering availability,
active/queued work, run outcomes, rejection/failure, duration, HTTP traffic, and
cache behavior.

**Tests:** `uv run pytest tests/test_grafana_dashboard.py` starts red before the
dashboard and provider exist, then passes against the checked-in JSON/YAML.

**Status:** Complete. The dashboard contract tests pass against the checked-in
JSON and all required existing metric families.

### Stage 22: Provision and Document the Dashboard

**Goal:** Add a Grafana file provider and version-controlled dashboard to the
existing observability bundle.

**Success Criteria:** Kustomize emits provider/dashboard ConfigMaps; Grafana can
load the dashboard without manual query construction; README documents mounting
the generated files and the meaning of each operational signal.

**Tests:** Dashboard contract test, JSON parsing, `kubectl kustomize
deploy/observability`, and `kubectl apply --dry-run=client -k deploy/observability`.

**Status:** Complete. Kustomize emits the provider and dashboard ConfigMaps, and
README documents the required Grafana mounts.

### Stage 23: Verify Queries and the Rendered Grafana View

**Goal:** Prove the dashboard against the running local Prometheus/Grafana stack.

**Success Criteria:** Every PromQL expression parses successfully, the dashboard
loads with the expected panels and live values in Grafana, browser console errors
are absent, and the repository completion gates pass.

**Tests:** Prometheus API query checks, Grafana API import/health checks, Playwright
MCP desktop validation, `make check`, and `git diff --check`.

**Status:** Complete. Prometheus expressions, Grafana schema/import, and the local
Playwright MCP render are recorded in `docs/evidence/task-016-grafana-dashboard.md`.

### Stage 24: Synchronize Browser-Local History Across Tabs

**Goal:** Keep the existing browser-local run history consistent when multiple
same-origin tabs submit runs at nearly the same time.

**Success Criteria:** A submission in one tab appears in the other open tabs without
refreshing; concurrent additions are merged instead of overwritten; clear-history,
expired-run pruning, and unknown-run removal continue to work; no server-wide
history endpoint or ownership semantics are introduced.

**Tests:** Add deterministic client tests for merging concurrent history entries;
use Playwright MCP with two tabs sharing one browser profile to submit separate runs,
observe both entries in both tabs, and verify the existing configured checks.

**Status:** Complete. Merge-on-write, storage-event synchronization, stale
revalidation protection, client regression coverage, and the two-tab Playwright MCP
flow are recorded in `docs/evidence/task-017-browser-history-sync.md`.

### Stage 25: Make the Portal Status Dashboard Range-Aware

**Goal:** Keep the portal status dashboard useful after a burst of requests has
gone idle, while preserving the distinction between selected-range statistics and
current active/queued work.

**Success Criteria:** Three-hour completed/failed/rejected cards show integral
counts; rate/error/cache panels render zero during quiet periods; duration and HTTP
quantiles use the selected range; and the instance selector excludes unrelated or
retired portal series.

**Tests:** Dashboard contract tests, JSON parsing, PromQL checks against the running
Prometheus instance, Kustomize rendering, Grafana reload, and Minikube rollout.

**Status:** Complete. The range-aware queries, portal-only instance selector,
PromQL checks, Minikube Grafana import, and Playwright MCP validation are recorded
in `docs/evidence/task-018-range-aware-grafana-dashboard.md`.

### Stage 26: Expose Rank-One Topology and Kubernetes Guidance

**Goal:** Show the rank-one `(p)worker`, `(d)worker`, `(p)tp`, and `(d)tp`
values returned by the portal and explain their Kubernetes pod, GPU, network,
and scheduling implications.

**Prerequisites:** ADR-010 is Accepted by the repository owner.

**Success Criteria:**

- The completed-run contract selects rank 1 independently for `agg` and
  `disagg` and preserves unavailable topology values honestly.
- Worker counts are presented as pod replicas; TP values are presented as GPUs
  per worker/pod, with no TP-to-replica inference.
- The responsive comparison view includes the topology values and concise
  network/scheduling guidance.
- Configured checks and Playwright MCP desktop, narrow, and keyboard scenarios
  pass.

**Tests:** `tests/test_comparison.py`, `tests/test_app.py`, and the browser
scenarios recorded in a new task evidence report.

**Status:** Requires correction under Proposed ADR-011. The previous evidence
must not be treated as valid for aggregated Pod sizing.

### Stage 27: Correct Mode-Aware Topology Semantics

**Goal:** Remove fabricated aggregated `(p)/(d)` fields and keep Kubernetes
sizing guidance limited to topology fields actually supplied by each mode.

**Prerequisites:** ADR-011 must be Accepted by the repository owner.

**Success Criteria:**

- Aggregated rank-one rows show their actual `tp`, `pp`, `dp`, and GPU fields;
  aggregated Pod replicas remain explicitly unavailable without a worker contract.
- Disaggregated rank-one rows use `(p)/(d)worker` for replicas only when present,
  and `(p)/(d)tp` for GPUs per worker Pod.
- Fake fixtures no longer synthesize unsupported aggregated fields.
- API, UI, Playwright MCP, and configured completion gates pass.

**Tests:** `tests/test_comparison.py`, `tests/test_app.py`, and the corrected
browser scenarios recorded in a new evidence report.

**Status:** Blocked pending ADR-011 acceptance.

### OpenTelemetry Extension Risks and Rollback

- Explicit `spawn` can change AIConfigurator startup latency and memory behavior;
  retain the current execution contract and stop if the real container evidence
  invalidates ADR-008's acceptable-overhead assumption.
- Duplicate initialization can create duplicate spans or metric registration errors;
  app-factory idempotence is a Stage 16 gate.
- Unsampled traces can leave correlated log IDs without a stored Tempo trace. Keep
  sampling explicit and document this expected outcome rather than fabricating a
  link target.
- Grafana correlation depends on exact field names, stable data-source UIDs, and an
  adequate time window. Provision and test both navigation directions together.
- Telemetry must remain optional to business correctness. Disable the SDK and remove
  the additive Alloy/Grafana configuration to roll back without changing run API,
  result, artifact, cache, history, or capacity behavior.

## References

- [AIConfigurator README](https://github.com/ai-dynamo/aiconfigurator/blob/main/README.md)
- [AIConfigurator CLI User Guide](https://github.com/ai-dynamo/aiconfigurator/blob/main/docs/cli_user_guide.md)
- [AIConfigurator Support Matrix](https://ai-dynamo.github.io/aiconfigurator/support-matrix/)
- [Anthropic Frontend Design plugin](https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design)
- [Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines)
