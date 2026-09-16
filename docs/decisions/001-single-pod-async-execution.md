# ADR-001: Single-Pod Asynchronous Execution

## Status

**Proposed**

## Decision Owner

Repository owner / take-home candidate.

## Context

AIConfigurator sweeps are CPU-bound and take seconds to minutes. The portal must
return status, remain healthy during computation, and fit an 8–10 hour take-home
scope. The repository has no existing application stack. AIConfigurator publishes a
documented Python API whose `cli_default` result exposes structured `best_configs`,
and the same invocation can generate deployment artifacts with `save_dir`.

The decision couples four boundaries that fail together: web/API stack, async API
shape, process isolation, and admission control. The artifact persistence decision
is separated into ADR-002.

## Decision Drivers

- Keep health and status handling separate from CPU-heavy execution.
- Return a run ID immediately and expose explicit lifecycle states.
- Preserve structured results without parsing human-oriented terminal output.
- Bound CPU use and queued work when many users submit simultaneously.
- Minimize infrastructure and code that do not contribute to the must-have demo.
- Leave an understandable migration path to a durable worker architecture.

## Options Considered

### Option A: Run the SDK Inline in the Request Handler

- **Benefits:** Fewest components; direct access to structured results.
- **Costs:** The HTTP request remains open and ties up server capacity.
- **Failure modes:** Client/proxy timeout, event-loop starvation, and an SDK failure
  affecting the web process.
- **Operability:** No natural queue/status boundary; poor fit for probes and
  concurrent requests.
- **Reversibility:** Easy to start, but lifecycle semantics would need replacement.

### Option B: Async API with One Isolated Local Worker Process

- **Benefits:** Immediate `202` response; web process remains available; process
  boundary contains CPU work and most dependency failures; the documented Python
  API provides structured DataFrames and generated files without stdout parsing.
- **Costs:** Run metadata and queue are local to one replica; restart recovery is not
  provided; child-process lifecycle and error propagation need tests.
- **Failure modes:** Pod termination loses active work; a wedged child needs a
  timeout/termination path; queued jobs disappear on restart.
- **Operability:** One active run and at most four queued runs make saturation
  observable and predictable. Additional submissions receive `429` plus
  `Retry-After`. JSON logs and metrics cover queue depth, active runs, completion,
  failure, rejection, and duration.
- **Testability:** The worker boundary is an interface. Tests use a fake adapter;
  one container smoke test uses the pinned real SDK.
- **Security:** Typed and validated arguments call the SDK directly, so browser input
  is never evaluated by a shell.
- **Reversibility:** The job service interface can later be backed by a durable queue
  without replacing browser/API contracts.

### Option C: Dedicated Worker Deployment with Durable Queue or Kubernetes Jobs

- **Benefits:** Independent scaling and resources, durable coordination, and better
  restart behavior. A Kubernetes Job can give each run explicit resources.
- **Costs:** Requires queue/database or Kubernetes API permissions, more manifests,
  cleanup/reconciliation code, and more failure modes than the time budget supports.
- **Failure modes:** Broker/control-plane outages, orphaned jobs, retry duplication,
  and RBAC errors.
- **Operability:** Best long-term isolation, but significantly more systems to demo
  and explain.
- **Reversibility:** Strong long-term foundation but costly to simplify.

## Recommendation

Choose Option B for the assignment:

- Python/FastAPI serves a small Jinja2/native-JavaScript page and JSON endpoints.
- `POST /api/runs` validates input, admits bounded work, and returns `202` with the
  run ID and status URL.
- `GET /api/runs/{id}` returns `queued`, `running`, `completed`, or `failed`; the
  browser polls every two seconds and stops at a terminal state.
- A single local worker process calls the pinned AIConfigurator Python SDK,
  normalizes `best_configs` into portal-owned result records, and writes generated
  artifacts to the run directory. It has a configured wall-clock timeout.
- One run executes at a time and four may wait. A full queue returns `429` with
  `Retry-After`; it never makes readiness false merely because the service is busy.
- Uvicorn runs one web worker and the Kubernetes Deployment runs one replica because
  job state is local. The rollout strategy is `Recreate`.
- CPU-heavy library thread counts are capped initially so the web process retains
  scheduling time. The smoke/load check tunes a provisional two-CPU request/limit
  rather than claiming it is correct before measurement.
- `/health/live` checks the web process/event loop. `/health/ready` checks that the
  service is initialized and accepting traffic, and becomes false during graceful
  shutdown. Neither endpoint performs an AIConfigurator run.

Polling is preferable here to SSE/WebSockets because job updates are low-frequency,
the API stays stateless from the client's perspective, and reconnect logic is
trivial. A two-second interval bounds demo load while showing visible progress; the
server owns the interval through a response hint so it can change later.

## Consequences

- **Positive:** All must-have behavior fits one image and one Deployment while CPU
  work remains outside the web process.
- **Positive:** Structured SDK data is easier to validate and normalize than CLI
  text, while the child process retains failure isolation.
- **Negative:** Only one replica is valid, and a restart loses queued/running state.
- **Negative:** Process isolation is not resource isolation; the web and child share
  the pod cgroup and must be tested under CPU pressure.
- **Negative:** The SDK contract may change, so the dependency is pinned and the
  adapter owns all version-specific translation.
- **Follow-up:** Move the same job contract to a durable queue/worker or Kubernetes
  Jobs when multi-replica availability, long runs, or per-team quotas are required.

## Validation

1. In a Linux x86-64 build, pin one AIConfigurator version and execute the assignment
   smoke input with artifact generation.
2. Record the structured result columns, generated artifact tree, elapsed time,
   maximum resident memory, and first-run network behavior.
3. Prove API state transitions with a fake adapter and with the real smoke run.
4. Submit more than the active-plus-queued capacity and verify deterministic `429`
   responses without growing the queue.
5. Continuously probe live/ready/status during a CPU-bound run under the Kubernetes
   CPU limit and record response latency.
6. Terminate the pod during a run and confirm the documented loss behavior.

## What Would Change This Decision

- Runs regularly exceed a few minutes or require retry/resume semantics.
- More than one portal replica, more than one concurrent sweep, or rolling updates
  without job loss become requirements.
- Queued work must survive pod replacement or be scheduled with per-job resources.
- AIConfigurator removes or destabilizes the documented Python API while retaining
  a stable machine-readable CLI contract.
- Per-user ownership, quotas, cancellation, or priority scheduling is required.

## Links

- Related requirements: `docs/project-brief.md`
- Related tasks: TASK-001 through TASK-006 in `TASKS.md`
- External evidence: AIConfigurator README and CLI User Guide linked from
  `IMPLEMENTATION_PLAN.md`
