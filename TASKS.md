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

- [~] **TASK-006 — Verify and document the handoff**
  - **Outcome:** A reviewer can reproduce and understand the solution and run a
    reliable 15-minute demo.
  - **Scope:** Full checklist, Playwright MCP, clean-checkout proof, README,
    architecture/ADR/task reconciliation, known limitations, demo script, diff and
    commit review.
  - **Dependencies:** TASK-005.
  - **Verify:** Every applicable item in `docs/verification-checklist.md` has exact
    evidence; all configured checks, build, integration, and `git diff --check`
    pass; git status contains only intentional files.
  - **Evidence:** Browser success evidence is in
    `docs/evidence/task-006-handoff.md`; README and narrow/keyboard browser cases
    remain open.

## Status Rules

- `[ ]` Not started or blocked; add a blocker note when applicable.
- `[~]` In progress; only one task should normally have this status.
- `[x]` Acceptance criteria are met and verification evidence is recorded.
