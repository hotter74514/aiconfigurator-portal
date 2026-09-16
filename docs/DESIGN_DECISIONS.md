# Design Decisions

This index records material decisions made for this project. The harness does not pre-populate decisions because architecture must be derived from project requirements and evidence.

Create a record from decisions/000-template.md when a choice is consequential, difficult to reverse, or affects a public boundary. Do not use ADRs for routine local implementation details.

| ADR | Decision | Status | Owner |
|---|---|---|---|
| [ADR-001](decisions/001-single-pod-async-execution.md) | Single-pod asynchronous execution | Proposed | Repository owner |
| [ADR-002](decisions/002-ephemeral-run-storage.md) | Ephemeral run and artifact storage | Proposed | Repository owner |

## Lifecycle

- **Proposed**: options and a recommendation are ready for review; implementation is blocked.
- **Accepted**: the decision owner approved implementation.
- **Rejected**: the proposal was considered and declined.
- **Superseded**: a newer ADR replaces the decision; link both records.

## Approval Protocol

The decision owner reviews the evidence, alternatives, trade-offs, and validation plan. If implementation evidence invalidates an accepted decision, stop affected work and propose a superseding ADR instead of silently changing direction.
