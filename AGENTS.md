# Repository Guidelines

## Mission

Deliver the outcomes in docs/project-brief.md through small, verifiable changes. Optimize for correctness, clear intent, explicit trade-offs, and a working end-to-end path. Do not infer product requirements or architecture from this harness.

## Read First

Before starting work:

1. Read docs/project-brief.md, ARCHITECTURE.md, ROADMAP.md, and TASKS.md.
2. Read the relevant accepted records under docs/decisions/.
3. Inspect the relevant implementation, tests, configuration, and git status.
4. Select one task with explicit acceptance criteria.

When documentation conflicts with executable behavior, call out the conflict and verify which source is authoritative.

## Architecture Decision Gate

Do not silently make a material or hard-to-reverse decision. Examples include public interfaces, data ownership, persistence, security boundaries, external dependencies, execution model, deployment topology, and compatibility guarantees.

For a material decision:

1. State the decision and evidence that makes it necessary.
2. Describe two or three viable options.
3. Compare complexity, failure modes, operability, testability, security, and reversibility.
4. Recommend the smallest defensible option.
5. Write a Proposed ADR from docs/decisions/000-template.md.
6. Stop before implementation until the project owner marks it **Accepted**.

Do not create ADRs for routine, local, reversible implementation choices.

## Implementation Loop

1. Reproduce or specify the current behavior.
2. Add or update a test that expresses the desired behavior when practical.
3. Implement the smallest complete change.
4. Refactor only with the relevant checks passing.
5. Run narrow checks first, then the configured project checks.
6. Update task status and documentation that no longer matches reality.
7. Review the diff for unrelated changes, secrets, generated files, and missing failure handling.

Prefer existing project patterns and tools. Add dependencies only when their value and maintenance cost are clear. Never weaken or disable a check to make a change pass.

## Safety Boundaries

Never commit credentials, tokens, private data, or local environment files. Require explicit user approval before production changes, destructive operations, permission changes, external messages, spending, or access to sensitive data. Use test doubles only at documented boundaries, and never represent simulated evidence as a real integration result.

After three materially different failed attempts at the same issue, stop and report the attempts, exact errors, likely cause, and reasonable alternatives.

## Git

Use a focused branch and small commits that preserve a reviewable history. Follow the repository's existing commit convention; otherwise use concise imperative or Conventional Commit subjects. Do not bypass hooks or rewrite shared history without explicit approval.

## Completion Gate

Before handoff:

- Run every applicable configured formatter, linter, type checker, test, build, and integration check.
- Execute the behavior-level path in docs/verification-checklist.md.
- Run make check and git diff --check.
- Confirm git status contains only intentional changes.
- Report changed files, exact commands and outcomes, assumptions, limitations, and unverified areas.

Never claim a command, test, integration, or user flow passed unless it was actually executed.
