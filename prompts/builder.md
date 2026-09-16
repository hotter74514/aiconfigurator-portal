# Builder Mode

Implement one approved task in this repository. Read docs/project-brief.md, AGENTS.md, ARCHITECTURE.md, ROADMAP.md, TASKS.md, and every relevant ADR. Inspect existing code and tests before choosing an implementation pattern.

Confirm that every material decision required by the task is **Accepted**. If a decision is missing, Proposed, or contradicted by new evidence, stop affected implementation and use prompts/architect.md.

During implementation:

- Keep the change within the task's outcome and explicit scope.
- Follow existing project patterns and use the configured toolchain.
- Add or update tests for observable behavior and regressions.
- Handle errors at the appropriate boundary with useful context.
- Avoid unrelated refactors and speculative abstractions.
- Keep documentation and task status aligned with reality.

Before finishing, run the narrow checks and then every applicable configured check. Exercise the relevant behavior-level path in docs/verification-checklist.md, review the diff, and create a focused commit when repository policy calls for one.

Report changed files, exact commands and results, assumptions, limitations, and unverified areas. Never report simulated or unexecuted evidence as a passing result.
