# Tasks

Work on one task at a time in priority order unless dependencies require a documented exception. Every task needs an observable outcome and verification evidence.

## Starter Queue

- [ ] **TASK-000 — Define the project brief**
  - Outcome: Goals, users, non-goals, constraints, and acceptance criteria are explicit.
  - Verify: Project owner reviews docs/project-brief.md.
- [ ] **TASK-001 — Baseline the repository**
  - Outcome: Existing architecture, commands, tests, and known failures are recorded without speculation.
  - Verify: Commands in Makefile have been executed or marked unavailable with a reason.
- [ ] **TASK-002 — Plan the first vertical slice**
  - Outcome: The smallest end-to-end user outcome is split into ordered, testable tasks.
  - Verify: Required material decisions have Proposed ADRs and implementation remains blocked until acceptance.

Replace this starter queue after project discovery.

## Task Template

- **ID and title**: TASK-NNN — Imperative title
- **Outcome**: Observable behavior or artifact.
- **Scope**: Included work and explicit non-goals.
- **Dependencies**: Tasks or accepted ADRs required first.
- **Verify**: Exact automated and behavior-level checks.
- **Evidence**: Filled in when complete.

## Status Rules

- [ ] Not started or blocked; add a blocker note when applicable.
- [~] In progress; only one task should normally have this status.
- [x] Acceptance criteria are met and verification evidence is recorded.
