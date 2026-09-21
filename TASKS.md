# Tasks

Work in priority order. Only one implementation task is active at a time. Evidence
must contain exact commands and observations, not only a checked box.

## Active Queue

- [x] **TASK-000 — Approve the project boundary and material decisions**
  - **Outcome:** The owner confirms the assignment-derived acceptance criteria and
    accepts or revises ADR-001 and ADR-002.
  - **Scope:** Review execution model, async/polling API, SDK/process boundary,
    concurrency, probe semantics, ephemeral storage, retention, and restart loss.
    No application implementation.
  - **Dependencies:** None.
  - **Verify:** `docs/project-brief.md` contains no unresolved placeholders; accepted
    ADRs have an owner decision and `docs/DESIGN_DECISIONS.md` matches their status.
  - **Evidence:** Owner accepted ADR-001 and ADR-002; status recorded in
    `docs/DESIGN_DECISIONS.md`.

- [x] **TASK-001 — Prove the pinned AIConfigurator contract**
  - **Outcome:** A Linux x86-64 container completes the documented Qwen/H200 sweep
    through the Python SDK and produces inspectable structured results and artifacts.
  - **Scope:** Pin package/Python versions; smoke `cli_default`; capture schema,
    artifact tree, SLA behavior, timing, memory, and network/cache behavior. Do not
    build portal features.
  - **Dependencies:** TASK-000; Accepted ADR-001 and ADR-002; running Docker daemon.
  - **Verify:** Repeatable smoke command exits zero and evidence identifies the exact
    version, result columns, required artifact files, and observed resource use.
  - **Evidence:** See `docs/evidence/task-001-aiconfigurator-smoke.md`. The pinned
    Linux x86-64 image completed normal and strict-SLA runs; schema, artifacts,
    timing, memory, and the required `plotext` compatibility pin are recorded.

- [x] **TASK-002 — Establish the tested application skeleton**
  - **Outcome:** A minimal app and fake AIConfigurator adapter have reproducible
    format, lint, type, unit-test, build, and integration entry points.
  - **Scope:** Package/lockfile, app factory, typed adapter boundary, deterministic
    fixture, pytest/Ruff/type tooling, Make commands. No run execution yet.
  - **Dependencies:** TASK-001 defines the adapter contract.
  - **Verify:** A clean environment can install/import the app; a fake-adapter test
    passes; `make check` invokes configured commands; dependency lock is committed.
  - **Evidence:** See `docs/evidence/task-002-skeleton.md`. `make format`, `make
    lint`, `make typecheck`, `make test`, `make integration`, `make build`, and
    `git diff --check` passed; two upstream TestClient deprecation warnings remain.

- [x] **TASK-003 — Implement bounded asynchronous runs**
  - **Outcome:** Valid submissions receive `202` and progress through explicit states
    while CPU work runs in one isolated child process.
  - **Scope:** Typed request/result models, run service, process worker, timeout,
    one-active/four-queued admission, polling status, normalized errors, graceful
    shutdown. No HTML or artifact download.
  - **Dependencies:** TASK-002.
  - **Verify:** Tests cover validation, immediate response, legal transitions,
    successful and failed worker, timeout, unknown ID, queue-full `429`, and web
    responsiveness during CPU work.
  - **Evidence:** See `docs/evidence/task-003-004-run-flow.md`; lifecycle, bounded
    queue, timeout, validation, polling, and failure normalization are covered by
    passing fake-worker API tests.

- [x] **TASK-004 — Deliver the browser result and download flow**
  - **Outcome:** A user submits the form, watches status, reads ranked estimates, and
    downloads only that run's artifact ZIP.
  - **Scope:** Jinja/native-JS UI, form defaults, polling, results table, warning,
    completed-run ZIP, TTL cleanup, orphan cleanup. No chart/history/cache/auth.
  - **Dependencies:** TASK-003.
  - **Verify:** API/UI tests cover success/error states, ordering and required
    metrics, incomplete/unknown/expired download behavior, ZIP isolation, cleanup,
    and path containment.
  - **Evidence:** See `docs/evidence/task-003-004-run-flow.md`; HTML polling,
    normalized table, run-scoped ZIP, path containment, TTL, and orphan cleanup are
    implemented and tested.

- [x] **TASK-005 — Add operations and Kubernetes delivery**
  - **Outcome:** The portal is observable, containerized, and deployable as one
    resource-bounded Kubernetes replica.
  - **Scope:** JSON logs, Prometheus metrics, live/ready probes, non-root image,
    Deployment/Service, resource/storage limits, Recreate rollout, shutdown.
  - **Dependencies:** TASK-004.
  - **Verify:** Automated observability/probe tests; Linux image smoke; client-side
    manifest validation; probe latency during real CPU work; local-cluster flow when
    a cluster is available.
  - **Evidence:** See `docs/evidence/task-005-operations.md`. Observability,
    non-root image, real container run/download, manifest shape, and a live
    Minikube rollout are recorded.

- [x] **TASK-006 — Verify and document the handoff**
  - **Outcome:** A reviewer can reproduce and understand the solution and run a
    reliable 15-minute demo.
  - **Scope:** Full checklist, Playwright MCP, clean-checkout proof, README,
    architecture/ADR/task reconciliation, known limitations, demo script, diff and
    commit review.
  - **Dependencies:** TASK-005.
  - **Verify:** Every applicable item in `docs/verification-checklist.md` has exact
    evidence; all configured checks, build, integration, and `git diff --check`
    pass; git status contains only intentional files.
  - **Evidence:** Browser, container, and local-cluster evidence is in
    `docs/evidence/task-006-handoff.md` and the linked task reports. The repository
    owner confirmed that TASK-006 validation has no known issues.

- [x] **TASK-007 — Expose the Pareto frontier visualization**
  - **Outcome:** A completed run shows its verified run-scoped Pareto artifact with
    accessible context and the ranked-table fallback.
  - **Scope:** Verify generated artifact semantics; add contained visualization
    metadata/endpoint; render captions and warnings. No recomputation from top-N rows
    or chart dependency.
  - **Dependencies:** TASK-006; Accepted ADR-003; pinned-container evidence.
  - **Verify:** Adapter/API tests cover lifecycle, media, missing, and unsafe paths;
    Playwright MCP covers desktop, narrow, keyboard, and fallback behavior; configured
    checks pass.
  - **Evidence:** See `docs/evidence/task-007-pareto-frontier.md`. The pinned SDK
    produced one verified 800×500 root-level PNG distinct from the mode top-N CSVs;
    the completed-run API serves it through a contained asset endpoint, and the
    Playwright MCP desktop/narrow/keyboard checks passed with the ranked table fallback.

- [x] **TASK-008 — Compare aggregated and disaggregated results**
  - **Outcome:** A completed two-mode run shows absolute metrics and correctly signed
    deltas without declaring a universal winner.
  - **Scope:** Verify rank semantics; add a server-owned optional comparison block;
    render mode values, deltas, and unavailable states. Pareto visualization is not
    required.
  - **Dependencies:** TASK-006; Accepted ADR-004.
  - **Verify:** Tests cover both/missing modes, missing values, zero baseline, row
    selection, signs, units, and rounding; Playwright MCP covers responsive and
    keyboard behavior; configured checks pass.
  - **Evidence:** See `docs/evidence/task-008-aggregated-disaggregated.md`. The
    server-owned rank-one comparison, signed deltas, rounding, missing-value
    handling, automated checks, and Playwright MCP desktop/narrow/keyboard flows
    pass.

- [x] **TASK-009 — Reuse identical completed results**
  - **Outcome:** A recent identical request avoids another sweep while receiving a
    fresh run ID and equivalent implemented result fields and artifact ZIP.
  - **Scope:** Canonical versioned cache key; successful completed bundles only;
    process-local TTL/count/byte bounds; LRU eviction; cache metrics. No durability or
    in-flight coalescing.
  - **Dependencies:** TASK-006; Accepted ADR-005.
  - **Verify:** Tests cover invalidation, hit/miss, distinct IDs, artifact equivalence,
    failure exclusion, eviction, expiry, metrics, and restart loss; configured checks
    pass.
  - **Evidence:** See `docs/evidence/task-009-bounded-result-cache.md`. The
    canonical versioned cache, fresh run IDs, artifact equivalence, failure and
    in-flight exclusion, TTL/LRU bounds, metrics, restart loss, and container
    smoke are recorded.

- [x] **TASK-010 — Restore browser-known runs**
  - **Outcome:** The same browser can reopen up to 20 still-valid runs without a
    server-wide run enumeration endpoint.
  - **Scope:** Capped browser `localStorage`, status revalidation/pruning, clear action,
    safe rendering, and honest loss/privacy wording. No cookie, account, ownership,
    authorization, or durable history.
  - **Dependencies:** TASK-006; Accepted ADR-006.
  - **Verify:** Client tests cover cap/prune/order/malformed storage; Playwright MCP
    covers refresh, expiry, clear, two-context separation, narrow, and keyboard
    behavior; configured checks pass.
  - **Evidence:** See `docs/evidence/task-010-browser-local-run-history.md`. The
    capped client history, status revalidation/pruning, clear action, refresh restore,
    isolated browser storage, narrow layout, and keyboard behavior are recorded.

- [x] **TASK-011 — Show anonymous shared capacity**
  - **Outcome:** Browsers can see aggregate active/queued pressure without seeing run
    or user details.
  - **Scope:** Allowlisted aggregate capacity endpoint, visibility-aware polling,
    neutral banner, and explicit no-account/no-reservation wording. No session,
    ownership, fairness, quota, or authentication.
  - **Dependencies:** TASK-006; Accepted ADR-007.
  - **Verify:** API tests cover all capacity states and fields; Playwright MCP covers
    two contexts, page visibility, narrow, and keyboard behavior; latency remains
    acceptable during a real sweep; configured checks pass.
  - **Evidence:** See `docs/evidence/task-011-anonymous-capacity.md` for API,
    Playwright MCP, and pinned-container real-sweep evidence.

- [x] **TASK-012 — Reconcile optional-feature handoff evidence**
  - **Outcome:** Every optional task represented as shipped has complete automated,
    browser, container, and applicable restart-loss evidence.
  - **Scope:** Checklist/evidence, clean flow, documentation reconciliation, diff and
    secret/generated-file review. Unstarted optional tasks remain deferred.
  - **Dependencies:** Every optional task selected for release.
  - **Verify:** All applicable formatter, linter, type, test, integration, build,
    browser, `make check`, and `git diff --check` gates pass.
  - **Evidence:** Partial evidence is in
    `docs/evidence/task-012-handoff-reconciliation.md`.

  - **Resolution:** The Kubernetes architecture mismatch and all cluster gates are
    resolved with an architecture-matched local image. The Playwright MCP profile
    was changed to isolated mode after the Chrome native download crash; keyboard
    download now saves and validates the run-scoped ZIP. Dependency failure/retry,
    all configured checks, and the final browser path are complete.

- [x] **TASK-013 — Refresh the portal UI as a precision planning workspace**
  - **Outcome:** The existing end-to-end workflow is visually polished, responsive,
    accessible, and easier to scan without changing application semantics.
  - **Scope:** Apply a pinned framework-agnostic frontend-design skill to the Jinja2
    template, a dedicated CSS token/style layer, and minimal presentation-state
    changes in native JavaScript. Audit the result with current web interface
    guidelines. No frontend framework, runtime CDN, external font dependency, API
    change, storage change, or new identity/security claim.
  - **Dependencies:** TASK-012; the Stage 11 design brief and baseline state matrix.
  - **Verify:** Tests cover static delivery and any extracted client view logic;
    Playwright MCP covers desktop, 390 px, 320 px, zoom, keyboard, reduced motion,
    complete/failed/saturated/fallback/history states, and the full submit-to-download
    flow; all configured completion gates pass.
  - **Evidence:** See `docs/evidence/task-013-ui-refresh.md` and the pinned design
    brief in `docs/evidence/task-013-design-brief.md`.

- [x] **TASK-014 — Deliver correlated OpenTelemetry signals through Grafana Alloy**
  - **Outcome:** Operators can follow one submitted run across the FastAPI request,
    queue, callback threads, and spawned AIConfigurator worker in Tempo; inspect
    trace-correlated JSON logs in Loki; query low-cardinality metrics in Prometheus;
    and navigate in both directions between the same Tempo trace and Loki logs from
    Grafana.
  - **Scope:** Implement the Accepted ADR-008 hybrid pipeline: explicit OpenTelemetry
    SDK bootstrap; FastAPI and logging instrumentation; OpenTelemetry metrics with a
    Prometheus reader; W3C Trace Context propagation through the bounded run manager
    and spawned worker; Alloy OTLP, Kubernetes-log, and Prometheus pipelines; stable
    Grafana Tempo/Loki/Prometheus data-source provisioning; bounded shutdown and
    outage behavior. Do not add OTLP log export, arbitrary baggage propagation,
    trace/run/model metric labels, trace IDs as Loki stream labels, durable queues,
    tail sampling, service graphs, or production credentials.
  - **Dependencies:** TASK-013; Accepted ADR-008; reachable Tempo, Loki, Prometheus,
    and Grafana endpoints for end-to-end verification.
  - **Verify:** Tests cover telemetry bootstrap and disabled mode, FastAPI spans,
    JSON trace/span injection, metric compatibility and cardinality, cache/rejection/
    failure/timeout paths, and a real spawned-worker propagation path using a known
    `traceparent`. Alloy and Kubernetes configurations validate; exporter/backend
    outage does not fail business traffic; Tempo, Loki, and Prometheus contain the
    expected signals. Playwright MCP proves **Logs for this span** opens the same
    trace's Loki logs and **View Trace** returns to the exact Tempo trace ID. Re-run
    the real container flow, configured repository checks, image build,
    `kubectl apply --dry-run=client`, and `git diff --check`.
  - **Evidence:** Implementation, local plus Minikube backend validation, and
    Playwright MCP bidirectional Grafana navigation are recorded in
    `docs/evidence/task-014-opentelemetry-alloy.md`, including a real trace ID,
    Tempo/Loki/Prometheus queries, datasource-proxy checks, and the visible
    **Logs for this span** / **View trace** flow, outage isolation, graceful
    shutdown, recovery, and negative propagation cases. All TASK-014 gates are
    complete.

- [x] **TASK-015 — Render the portal-owned Pareto trade-off surface**
  - **Outcome:** Completed estimates show a responsive, accessible trade-off
    surface with blue frontier points, slate dominated candidates, explicit axis
    directions, and a frontier summary sourced from the same full SDK sweep.
  - **Scope:** Normalize bounded `CLIResult.pareto_fronts` frames, classify only
    cross-mode dominance over those complete frames, render a native SVG and text
    summary, and retain the SDK PNG plus ranked table as fallback evidence. No
    browser recomputation from top-N rows and no chart runtime dependency.
  - **Dependencies:** TASK-014; Accepted ADR-009; pinned AIConfigurator 0.11.0
    `pareto_fronts` contract.
  - **Verify:** Unit tests cover objective direction, cross-mode dominance,
    malformed/missing columns, empty data, and bounded cardinality. API/cache tests,
    `make check`, image build, and Playwright MCP desktop/narrow/keyboard checks
    pass.
  - **Evidence:** Record the deterministic fixture, real SDK column inventory,
    rendered browser observations, and limitations in
    `docs/evidence/task-015-tradeoff-surface.md`.

- [x] **TASK-016 — Provision a Grafana portal status dashboard**
  - **Outcome:** Operators can open one provisioned dashboard and quickly determine
    whether the portal is observable, busy, saturated, slow, or failing.
  - **Scope:** Reuse the existing Prometheus datasource UID and low-cardinality
    portal/HTTP metrics. Add file provisioning, availability and workload summary
    stats, outcome/rate trends, run and HTTP latency, and cache behavior. Do not add
    application metrics, alert delivery, production credentials, or a new backend.
  - **Dependencies:** TASK-014 and a Prometheus-compatible backend containing the
    existing `/metrics` series.
  - **Verify:** Contract tests parse the dashboard and lock key PromQL; Kustomize
    and client-side Kubernetes validation pass; every expression succeeds against
    local Prometheus; Playwright MCP verifies the rendered Grafana dashboard and
    browser console; `make check` and `git diff --check` pass.
  - **Evidence:** Record exact checks, visible panels, live values, and limitations
    in `docs/evidence/task-016-grafana-dashboard.md`.

- [x] **TASK-017 — Synchronize browser-local history across tabs**
  - **Outcome:** Same-origin tabs observe each other's browser-local submissions,
    including near-simultaneous additions, without introducing server-wide history.
  - **Scope:** Merge-on-write, `storage` event synchronization, and regression/browser
    coverage. Preserve the existing cap, TTL, pruning, clear action, and local-only
    privacy boundary.
  - **Dependencies:** TASK-010; Accepted ADR-006 remains unchanged.
  - **Verify:** Client merge tests, two-tab Playwright MCP submission flow, `make
    check`, and `git diff --check` pass.
  - **Evidence:** See `docs/evidence/task-017-browser-history-sync.md` for exact
    client, Playwright MCP, and configured-check observations.

- [x] **TASK-018 — Make the portal status dashboard range-aware**
  - **Outcome:** A three-hour Grafana view preserves selected-range run counts and
    latency observations, renders zero for quiet rate/error/cache panels, and
    excludes unrelated or retired portal instances.
  - **Scope:** Adjust dashboard-only PromQL and the instance variable; do not add
    application metrics, alerts, credentials, or a new backend. Import the updated
    dashboard into the existing Minikube Grafana deployment.
  - **Dependencies:** TASK-016; the existing Prometheus-compatible metrics and
    Grafana service in the `aiconfigurator` Minikube profile.
  - **Verify:** Contract tests, `make check`, JSON/Kustomize validation, all 24
    PromQL targets against Minikube Prometheus, Grafana API import, and Playwright
    MCP at a three-hour range.
  - **Evidence:** See
    `docs/evidence/task-018-range-aware-grafana-dashboard.md` for exact commands,
    observed values, and the Grafana provisioning limitation.

- [x] **TASK-019 — Show rank-one topology and Kubernetes sizing guidance**
  - **Outcome:** The completed-run comparison shows rank-one `(p)worker`,
    `(d)worker`, `(p)tp`, and `(d)tp` values for both modes and explains how
    worker counts map to pod replicas while TP maps to GPUs per pod.
  - **Scope:** Extend the server-owned comparison contract under Accepted
    ADR-010; preserve missing values; add structured network and scheduling
    guidance in the existing Jinja/native-JavaScript UI. Do not apply manifests,
    claim cluster validation, or treat estimates as production guarantees.
  - **Dependencies:** TASK-008; Accepted ADR-010.
  - **Verify:** Comparison/API tests, `make check`, integration, client tests,
    container build, `git diff --check`, and Playwright MCP desktop, 390 px,
    keyboard, and console/network checks pass.
  - **Evidence:** See `docs/evidence/task-019-rank-one-topology.md`.

- [~] **TASK-020 — Correct mode-aware topology semantics**
  - **Outcome:** Aggregated results no longer receive fabricated prefill/decode
    worker fields or inferred Pod counts; disaggregated sizing remains available
    when the source fields exist.
  - **Scope:** Implement Proposed ADR-011, superseding the incorrect agg
    assumptions in ADR-010. Update API, fake fixtures, UI, tests, evidence, and
    guidance; do not infer Pod replicas from aggregated `tp` or GPU count.
  - **Dependencies:** TASK-019; Accepted ADR-011.
  - **Verify:** Mode-aware fixtures, unavailable-state tests, Playwright MCP,
    configured checks, container build, and `git diff --check`.
  - **Evidence:** To be recorded after ADR-011 acceptance.

## Status Rules

- `[ ]` Not started or blocked; add a blocker note when applicable.
- `[~]` In progress; only one task should normally have this status.
- `[x]` Acceptance criteria are met and verification evidence is recorded.
