# Design Decisions

This index records material decisions made for this project. The harness does not pre-populate decisions because architecture must be derived from project requirements and evidence.

Create a record from decisions/000-template.md when a choice is consequential, difficult to reverse, or affects a public boundary. Do not use ADRs for routine local implementation details.

| ADR | Decision | Status | Owner |
|---|---|---|---|
| [ADR-001](decisions/001-single-pod-async-execution.md) | Single-pod asynchronous execution | Accepted | Repository owner |
| [ADR-002](decisions/002-ephemeral-run-storage.md) | Ephemeral run and artifact storage | Accepted | Repository owner |
| [ADR-003](decisions/003-pareto-frontier-visualization.md) | Pareto frontier visualization source | Superseded by ADR-009 | Repository owner |
| [ADR-004](decisions/004-aggregated-disaggregated-comparison.md) | Aggregated and disaggregated result comparison | Accepted | Repository owner |
| [ADR-005](decisions/005-bounded-result-cache.md) | Bounded result cache | Accepted | Repository owner |
| [ADR-006](decisions/006-browser-local-run-history.md) | Browser-local run history | Accepted | Repository owner |
| [ADR-007](decisions/007-anonymous-capacity-awareness.md) | Anonymous multi-user capacity awareness | Accepted | Repository owner |
| [ADR-008](decisions/008-opentelemetry-alloy-pipeline.md) | OpenTelemetry and Grafana Alloy telemetry pipeline | Accepted | Repository owner |
| [ADR-009](decisions/009-portal-owned-tradeoff-surface.md) | Portal-owned trade-off surface visualization | Accepted | Repository owner |
| [ADR-010](decisions/010-rank-one-topology-and-kubernetes-guidance.md) | Rank-one topology fields and Kubernetes guidance | Superseded by ADR-011 | Repository owner |
| [ADR-011](decisions/011-mode-aware-topology-semantics.md) | Mode-aware topology semantics | Accepted; guidance portion superseded by ADR-012 | Repository owner |
| [ADR-012](decisions/012-remove-kubernetes-network-scheduling-guidance.md) | Remove generic Kubernetes network and scheduling guidance | Accepted | Repository owner |

## Lifecycle

- **Proposed**: options and a recommendation are ready for review; implementation is blocked.
- **Accepted**: the decision owner approved implementation.
- **Rejected**: the proposal was considered and declined.
- **Superseded**: a newer ADR replaces the decision; link both records.

## Approval Protocol

The decision owner reviews the evidence, alternatives, trade-offs, and validation plan. If implementation evidence invalidates an accepted decision, stop affected work and propose a superseding ADR instead of silently changing direction.
