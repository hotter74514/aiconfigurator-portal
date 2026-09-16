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

## Browser Testing

When a task requires browser-based validation, MUST use `playwright-mcp`. This includes page rendering, responsive viewport behavior, keyboard or accessibility flows, network-driven UI states, downloads, and screenshots. Do not substitute another browser automation tool; if `playwright-mcp` is unavailable, report the blocker instead of silently changing the test method. Record the exercised scenarios and observed results in the relevant task or verification report.

## Safety Boundaries

Never commit credentials, tokens, private data, or local environment files. Require explicit user approval before production changes, destructive operations, permission changes, external messages, spending, or access to sensitive data. Use test doubles only at documented boundaries, and never represent simulated evidence as a real integration result.

After three materially different failed attempts at the same issue, stop and report the attempts, exact errors, likely cause, and reasonable alternatives.

## Git

Use feature branches (`feat/run-api`, `feat/artifact-download`) and keep an inspectable, incremental history. Create focused Conventional Commits at approved milestones (`feat: add asynchronous run API`, `infra: add kubernetes deployment`, `docs: record design decisions`); do not squash the assignment into one commit or commit directly to `main` unless explicitly requested.

Every commit must include a descriptive body with a blank line after the subject and a bullet list of the substantive changes, for example:

```text
feat: refresh serving decision portal UI

- Add the responsive serving-decision console layout.
- Preserve the self-contained Jinja2 and native JavaScript boundary.
- Add regression coverage for the refreshed page.
```

The bullets must describe the actual changes in that commit; do not leave the body empty or rely on the subject alone.

The blank line and bullet separators must be real newline characters in the
commit message. Do not pass the two-character string `\n` as a substitute
for a line break. Before handing off a commit, verify its rendered message with
`git log -1 --format=fuller` (or inspect the raw message with
`git cat-file -p HEAD`).

## Completion Gate

Before handoff:

- Run every applicable configured formatter, linter, type checker, test, build, and integration check.
- Execute the behavior-level path in docs/verification-checklist.md.
- Run make check and git diff --check.
- Confirm git status contains only intentional changes.
- Report changed files, exact commands and outcomes, assumptions, limitations, and unverified areas.

Never claim a command, test, integration, or user flow passed unless it was actually executed.
