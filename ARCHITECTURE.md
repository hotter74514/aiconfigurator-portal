# Architecture

## Status

**Baseline recorded; target architecture is proposed, not accepted.** The repository
currently contains documentation and workflow scaffolding but no application code,
package manifest, container image, or deployment manifest. Proposed system choices
are recorded in ADR-001 and ADR-002.

## Current System Context

- **Users or callers:** No implemented callers. The assignment targets ML engineers
  using a browser and platform operators using Kubernetes/HTTP observability.
- **Primary outcome:** See `docs/project-brief.md`.
- **External systems:** AIConfigurator and its packaged/profile data; a Kubernetes
  API is only a deployment target for the portal and for downloaded artifacts.
- **Trust boundaries:** Browser input is untrusted; generated files are downloadable
  output and are never automatically applied to a cluster.

## Current Components

| Component | Responsibility | Interfaces | Owner |
|---|---|---|---|
| Engineering harness | Planning, decision, verification, and handoff workflow | Markdown and Make targets | Repository owner |
| Application | Not implemented | Unknown until ADR acceptance | Repository owner |
| AIConfigurator adapter | Not implemented | Must be verified against a pinned release | Repository owner |
| Deployment | Not implemented | Kubernetes shape proposed in ADR-001/002 | Repository owner |

## Proposed Data and Control Flow

This is a planning target and does not become the recorded architecture until the
related ADRs are accepted and verified:

    browser -> web/API -> bounded in-memory queue -> isolated worker process
                |                                      |
                +-> status/results <--- normalized result + artifact directory
                                                         |
                                                         +-> AIConfigurator SDK

The portal would expose polling rather than hold an HTTP request open. Artifacts and
run metadata would be local and ephemeral for the assignment scope.

## Verified Constraints

- The repository has no selected application language/framework or configured
  format, lint, type-check, test, build, or integration commands.
- The assignment requires container and Kubernetes delivery, health/readiness,
  structured logging, metrics, ranked results, and downloadable artifacts.
- The assignment identifies the AIConfigurator workload as CPU-bound and the
  published wheels as Linux x86-64 only.
- Browser validation is required to use the Playwright MCP configured in
  `.codex/config.toml`.

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

## Decision Links

- `docs/decisions/001-single-pod-async-execution.md` — Proposed.
- `docs/decisions/002-ephemeral-run-storage.md` — Proposed.
- `docs/DESIGN_DECISIONS.md` indexes decision status.
