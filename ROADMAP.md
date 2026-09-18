# Roadmap

The roadmap prioritizes a working, defensible must-have path within the assignment's
8–10 hour budget. Optional features do not begin until the delivery gate passes.

## P0 — Establish and Approve the Boundary

- [x] Translate the assignment into users, outcomes, acceptance criteria, non-goals,
  constraints, risks, and a definition of done.
- [x] Baseline the repository and local tools without inventing an application stack.
- [x] Propose the execution/API/worker and artifact lifecycle decisions with
  alternatives, failure modes, and validation plans.
- [x] Project owner reviewed the brief and marked ADR-001 and ADR-002 Accepted.

## P1 — Prove the Riskiest Boundary

- [x] Build a pinned Linux x86-64 environment and run the documented real
  AIConfigurator smoke input through its Python API.
- [x] Capture the result schema, generated artifacts, SLA behavior, runtime/memory,
  and network/cache requirements.
- [x] Establish the minimal tested application and fake-adapter seams; configure
  reproducible project commands.

## P2 — Deliver the Functional Vertical Slice

- [x] Submit a validated request and receive an opaque run ID immediately.
- [x] Execute one sweep in an isolated process with a bounded queue, timeout, and
  explicit queued/running/completed/failed state.
- [x] Poll and display ranked throughput/TTFT/TPOT/topology results in the web UI.
- [x] Download a run-scoped ZIP of generated deployment artifacts.
- [x] Show unsupported inputs, dependency failures, saturation, and estimate warnings
  honestly.

## P3 — Make It Operable and Deployable

- [x] Add correlated structured logs and low-cardinality Prometheus metrics.
- [x] Add distinct liveness/readiness behavior and verify responsiveness during CPU
  work.
- [x] Build a pinned non-root container and deploy one replica with sound probes,
  resource controls, graceful shutdown, and bounded `emptyDir` storage.
- [x] Validate manifests and execute the service, metrics, real run, result polling,
  and artifact download flow on the local Minikube cluster.

## P4 — Verify and Hand Off

- [x] Execute automated, container, browser, overload, restart, and artifact checks
  in `docs/verification-checklist.md`. TASK-012 completed the final browser path
  after switching the project-scoped Playwright MCP server to isolated mode.
- [x] Verify clean-checkout setup and the 15-minute demo path.
- [x] Complete README architecture, design decisions, operations, and known
  limitations from observed evidence.
- [x] Reconcile all planning/architecture documents, inspect commit history, and
  confirm the working tree contains only intentional files.

## P5 — Optional Results Insight and Ephemeral Convenience

This phase begins only after P4 passes. Each increment requires its corresponding
ADR to be Accepted and may be approved, implemented, or deferred independently.

- [x] ADR-003: verify and show the same run's Pareto artifact.
- [x] ADR-004: add an accessible agg/disagg comparison summary.
- [x] ADR-005: add a TTL/count/byte-bounded process-local result cache.
- [x] ADR-006: add capped browser-local recent-run history.
- [x] ADR-007: add anonymous aggregate capacity awareness.

Final optional-feature handoff reconciliation is complete. See TASK-012 and
`docs/evidence/task-012-handoff-reconciliation.md`; prior feature and cluster
evidence remains recorded.

## P6 — Optional UI Refresh

Begin only after TASK-012 reconciles the existing release evidence. Keep the current
Jinja2/native-JavaScript architecture and use design skills as bounded guidance, not
as authority to change product or system boundaries.

- [x] Capture a complete visual and interaction baseline with Playwright MCP.
- [x] Apply a pinned framework-agnostic frontend-design skill and semantic CSS token
  system to create a responsive precision-planning workspace.
- [x] Polish every asynchronous, comparison, visualization, history, capacity, and
  error state without changing its behavior or required disclosures.
- [x] Audit against current web interface guidelines and pass the full automated,
  browser, container, and documentation completion gates.

## P7 — Correlated OpenTelemetry Delivery

Proceed under Accepted ADR-008 while preserving the single-pod run lifecycle and
the existing `/metrics` contract.

- [x] Accept the hybrid OpenTelemetry, Alloy, and Grafana correlation architecture.
- [x] Instrument FastAPI, Python logs, and portal metrics with an explicit,
  lifecycle-owned OpenTelemetry bootstrap.
- [x] Propagate W3C Trace Context through queued work, callback threads, and the
  explicitly spawned AIConfigurator worker process.
- [x] Route traces to Tempo, JSON pod logs to Loki, and scraped metrics to
  Prometheus through bounded Alloy pipelines.
- [x] Provision stable Grafana data sources and prove Tempo-to-Loki and
  Loki-to-Tempo navigation with Playwright MCP.
- [x] Complete container, Kubernetes, outage, cardinality, and documentation gates
  for TASK-014.

## P8 — Portal-Owned Trade-off Surface

Proceed under Accepted ADR-009 without changing the run, cache, artifact, or
telemetry boundaries.

- [x] Normalize complete SDK `pareto_fronts` frames with explicit latency and
  throughput objective directions and bounded cross-mode dominance.
- [x] Render the responsive native SVG, legend, frontier summary, and keyboard-
  focusable point labels while retaining the SDK PNG and ranked table fallbacks.
- [x] Verify deterministic fixtures, API/cache serialization, configured checks,
  and Playwright MCP desktop/narrow browser behavior.

## P9 — Portal Status Dashboard

- [x] Provision a version-controlled Grafana dashboard from the existing
  low-cardinality Prometheus metrics.
- [x] Cover availability, traffic, run outcomes, saturation, latency, and cache
  behavior with explicit units and thresholds.
- [x] Validate every PromQL expression and render the dashboard in the local
  Grafana stack with Playwright MCP.

## Deferred

- **Additional Pareto dimensions:** require a new accepted ADR if users need
  interactive axis selection or dimensions beyond request latency and cluster
  throughput.
- **In-flight request coalescing:** defer until duplicate concurrent traffic justifies
  the added cancellation, failure, and ownership semantics.
- **Durable run history:** requires durable metadata and object/PVC storage first.
- **Multi-user authorization and quota:** requires an identity boundary, ownership
  model, and durable admission control.
- **Dedicated worker deployment or Kubernetes Job per run:** promote when runs are
  long, must survive rollout, need per-job resources, or require multiple replicas.
- **Real benchmark feedback loop:** requires GPU access and belongs after the
  recommendation workflow, not inside this take-home scope.
