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
- [~] Validate manifests and execute the flow on an available local cluster (no
  usable local cluster; kubeconfig requires unavailable AWS credentials).

## P4 — Verify and Hand Off

- [ ] Execute automated, container, browser, overload, restart, and artifact checks
  in `docs/verification-checklist.md`.
- [ ] Verify clean-checkout setup and the 15-minute demo path.
- [ ] Complete README architecture, design decisions, operations, and known
  limitations from observed evidence.
- [ ] Reconcile all planning/architecture documents, inspect commit history, and
  confirm the working tree contains only intentional files.

## Deferred

- **Pareto chart and richer agg/disagg comparison:** promote only after every
  must-have gate passes with remaining time.
- **Deterministic result cache:** promote when repeat traffic justifies explicit
  invalidation across inputs, AIConfigurator/profile/backend versions, and portal
  schema.
- **Durable run history:** requires durable metadata and object/PVC storage first.
- **Multi-user authorization and quota:** requires an identity boundary, ownership
  model, and durable admission control.
- **Dedicated worker deployment or Kubernetes Job per run:** promote when runs are
  long, must survive rollout, need per-job resources, or require multiple replicas.
- **Real benchmark feedback loop:** requires GPU access and belongs after the
  recommendation workflow, not inside this take-home scope.
