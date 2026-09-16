# Project Brief

## Status

**Ready for owner review.** This brief is derived from the Serving Configuration
Portal take-home assignment. Proposed architecture choices remain subject to ADR
acceptance.

## Problem

ML engineers need to turn a model, GPU budget, and latency objectives into a
defensible LLM serving configuration. AIConfigurator can estimate and rank those
configurations without consuming GPU time, but its CLI, support matrix, and
generated file layout are too specialized for routine self-service use.

The portal must expose the smallest safe paved road: submit a supported planning
request, observe its progress, inspect ranked estimates, and download the generated
deployment artifacts without installing AIConfigurator locally.

## Users and Stakeholders

- **Primary user:** ML engineers and researchers planning an LLM deployment.
- **Secondary users:** AI/ML platform engineers doing capacity and configuration
  planning.
- **Decision owner:** Repository owner / take-home candidate.
- **Operational owner:** The AI/ML platform team that would operate the portal.

## Desired Outcomes

- A user completes the form and receives a run identifier immediately.
- A user can distinguish queued, running, completed, and failed runs.
- A completed run shows ranked configurations with predicted throughput, TTFT,
  TPOT, serving mode, and enough topology detail to distinguish the options.
- A user can download the deployment files produced by the same run.
- An operator can deploy the portal locally or to Kubernetes and determine whether
  it is healthy, ready, saturated, or failing.
- The UI makes clear that predictions are planning estimates and require a real
  benchmark before production rollout.

## Acceptance Criteria

- [ ] The page accepts model, GPU system, total GPU count, TTFT, and TPOT, with
  documented defaults; input/output token lengths may be exposed with defaults.
- [ ] Valid submission returns an opaque run ID and status URL without holding the
  request open for the sweep.
- [ ] The status endpoint reports `queued`, `running`, `completed`, or `failed`, and
  terminal failure responses contain an actionable but sanitized reason.
- [ ] A successful run displays at least the top five configurations, ranked
  consistently, including predicted throughput, TTFT, and TPOT.
- [ ] Results that do not meet the requested SLA are either excluded or visibly
  identified; the exact AIConfigurator behavior is verified in the initial spike.
- [ ] A completed run exposes a ZIP download containing the AIConfigurator-generated
  deployment artifacts; incomplete and unknown runs fail clearly.
- [ ] Unsupported or invalid model/system requests do not start an unbounded job and
  return a useful error state.
- [ ] Concurrent execution is bounded. Excess submissions receive an explicit
  retryable response rather than exhausting the pod.
- [ ] `/health/live`, `/health/ready`, and `/metrics` remain responsive during a
  sweep and have documented semantics.
- [ ] Logs are structured and correlate lifecycle events by run ID without logging
  artifact contents or secrets.
- [ ] A Linux x86-64 container can execute one documented real AIConfigurator smoke
  case, and the application container is reproducibly buildable.
- [ ] Raw Kubernetes manifests deploy the service with probes, resource requests and
  limits, temporary artifact storage, and a non-root security context.
- [ ] Unit/integration checks and the browser scenarios in
  `docs/verification-checklist.md` pass, followed by `make check` and
  `git diff --check`.

## Non-Goals

- Authentication, authorization, team isolation, or per-user quota enforcement.
- Durable run history, high availability, cross-replica job coordination, or
  bookmarked results surviving a pod replacement.
- Result caching, Pareto charts, or a rich comparison experience.
- Deploying the generated serving workload or proving the estimate on real GPUs.
- TLS, production secrets management, autoscaling, or a production-grade queue.
- Modifying AIConfigurator or supporting arbitrary local model paths and generator
  overrides from portal users.

## Constraints

- The assignment allows 8–10 hours of focused work, so every must-have precedes
  optional work.
- AIConfigurator is an external dependency and must not be modified.
- The assignment states that published AIConfigurator wheels are Linux x86-64 only;
  local macOS development must execute the real dependency through Docker.
- A sweep is CPU-bound and can run for seconds to minutes. Request handling and
  health checks must not execute the sweep inline.
- No GPU is required for prediction, and no generated manifest is automatically
  applied to a cluster.
- AIConfigurator output is an estimate, not a production performance guarantee.
- Browser validation must use the repository's configured Playwright MCP server.
- Exact AIConfigurator version, supported inputs, SDK result columns, and generated
  artifact layout must be established by a pinned-container smoke test before the
  adapter contract is implemented.

## Existing Dependencies and Boundaries

- **Required integration:** AIConfigurator `default` sweep and artifact generation.
- **External data:** AIConfigurator's packaged performance profiles and model/system
  support behavior.
- **Deployment boundary:** The portal produces and downloads manifests; it never
  applies them.
- **Trust boundary:** Browser input is untrusted. It is validated and mapped to
  typed SDK arguments, never interpolated into a shell command or filesystem path.
- **Repository boundary:** The current repository contains an engineering harness
  only; no application framework or command stack is yet established.

## Risks and Unknowns

| Risk or unknown | Impact | Evidence needed | Owner |
|---|---|---|---|
| Published package/version and Linux architecture compatibility | Blocks the real run | Build a pinned Linux image and execute the assignment smoke case | Implementer |
| SDK result schema and artifact tree may vary by version/mode | Results or downloads could be incorrect | Capture `best_configs` columns and generated tree from the pinned version | Implementer |
| Model metadata lookup may require network access on first run | Demo can fail offline | Run twice with a clean/cache-warm image and document network/cache behavior | Implementer |
| CPU saturation can delay web health handling | Kubernetes may restart a healthy pod | Load-test status and probes during a real sweep under the declared CPU limit | Implementer |
| Ephemeral state is lost on restart | In-flight and completed runs disappear | Document and test restart behavior; revisit only if durability becomes required | Decision owner |
| Generated YAML may look production-authoritative | Users could deploy an unvalidated estimate | Persistent UI/download warning and documented benchmark gate | Implementer |

## Definition of Done

The shortest browser path works from a clean checkout: build and start the
container, submit the documented smoke input, observe status transitions, inspect
ranked estimates, and download the matching artifact ZIP. Automated tests cover
validation, lifecycle, result normalization, downloads, saturation, and dependency
failure. Kubernetes manifests pass static validation and are exercised on a local
cluster when available. README design decisions and limitations match the accepted
ADRs and observed behavior, all configured checks pass, and unverified areas are
listed explicitly.
