# Architecture

## Status

**Implemented baseline and optional extension; ADR-001 through ADR-007 are
Accepted.** The repository contains the application, pinned dependency lock,
container image definition, Kubernetes deployment manifest, result insight features,
bounded cache, browser-local history, and anonymous capacity awareness.

## Current System Context

- **Users or callers:** ML engineers use the browser/API; platform operators use
  Kubernetes and the HTTP observability endpoints.
- **Primary outcome:** See `docs/project-brief.md`.
- **External systems:** AIConfigurator and its packaged/profile data; a Kubernetes
  API is only a deployment target for the portal and for downloaded artifacts.
- **Trust boundaries:** Browser input is untrusted; generated files are downloadable
  output and are never automatically applied to a cluster.

## Current Components

| Component | Responsibility | Interfaces | Owner |
|---|---|---|---|
| Engineering harness | Planning, decision, verification, and handoff workflow | Markdown and Make targets | Repository owner |
| Application | FastAPI app factory, liveness, anonymous capacity awareness, and metadata boundary | `portal.app:create_app`; `/health/live`; `/api/capacity`; `/` | Repository owner |
| Adapter boundary | Typed request/result protocol, visualization metadata, and deterministic fake | `portal.adapters.AiconfiguratorAdapter` | Repository owner |
| Completed-result cache | Bounded process-local cache for successful normalized bundles, fresh run IDs, and artifact materialization | `portal.cache.BoundedResultCache`; run-manager internal | Repository owner |
| Browser-local run history | Capped, status-revalidated convenience index for one browser profile | `localStorage`; `/api/runs/{id}` status endpoint | Repository owner |
| Real AIConfigurator adapter | Runs the pinned SDK in an isolated worker and normalizes results/artifacts/verified Pareto output | `portal.aiconfigurator:run_ai_configurator` | Repository owner |
| Deployment | Non-root single-replica container on Kubernetes with probes and bounded ephemeral storage | `Dockerfile`; `deploy/portal.yaml`; ClusterIP HTTP service | Repository owner |

## Implemented Data and Control Flow

    browser -> web/API -> bounded in-memory queue -> isolated worker process
                |                                      |
                +-> status/results <--- normalized result + artifact directory
                                                         |
                                                         +-> AIConfigurator SDK

The portal returns an opaque run ID immediately and the browser polls the status
endpoint. Completed immutable bundles may be reused from the bounded in-process
cache under a versioned canonical request key, but every cache hit receives a fresh
run ID. Artifacts and run metadata remain local and ephemeral.

## Verified Constraints

- The application uses Python 3.11, FastAPI, Uvicorn, pytest, Ruff, mypy, and uv;
  commands are configured in `Makefile` and resolved in `uv.lock`.
- The assignment requires container and Kubernetes delivery, health/readiness,
  structured logging, metrics, ranked results, and downloadable artifacts.
- The assignment identifies the AIConfigurator workload as CPU-bound and the
  published wheels as Linux x86-64 only.
- Successful completed bundles may be reused in-process only when the canonical
  request key includes the pinned AIConfigurator, profile, generator-mapping, and
  portal-normalization namespace; cache state is lost on restart.
- Browser validation is required to use the Playwright MCP configured in
  `.codex/config.toml`.
- Browser-local history is capped at 20 entries and stores no server-wide index;
  malformed, expired, and unknown IDs are pruned through the existing status API.
- Anonymous capacity awareness is a read-only aggregate view of this process's
  active and queued runs. It exposes no run IDs, request data, timestamps, IPs,
  cookies, or user labels; `admission_open` is informational and does not reserve
  a slot.

## Quality Attributes

- **Responsiveness:** Status and health requests remain responsive while one sweep
  runs; verify under the Kubernetes CPU limit.
- **Bounded resource use:** One active sweep and a small bounded queue; verify that
  excess work is rejected with a retryable response.
- **Reproducibility:** Pin dependencies and prove the documented smoke case in the
  built Linux image.
- **Operability:** Correlated JSON logs and low-cardinality run/latency/queue metrics.
- **Safety:** Never shell-interpolate user input or auto-apply generated manifests.
- **Honest output:** Every result/download view says estimates require real benchmark
  validation.
- **Traceable visualization:** The portal serves only the pinned SDK's contained
  `pareto_frontier.png`; exact values remain available in the ranked table.
- **Honest multi-user boundary:** Browser-local history and anonymous capacity
  counts add convenience without claiming identity, ownership, privacy, fairness,
  or durable state.

## Decision Links

- `docs/decisions/001-single-pod-async-execution.md` — Accepted.
- `docs/decisions/002-ephemeral-run-storage.md` — Accepted.
- `docs/DESIGN_DECISIONS.md` indexes decision status.
