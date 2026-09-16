# Review a Change

Perform a read-only review of the specified diff or current working tree.

Read docs/project-brief.md, AGENTS.md, ARCHITECTURE.md, docs/DESIGN_DECISIONS.md, the relevant task, accepted ADRs, and affected tests. Review behavior and risk before style.

Prioritize:

- Incorrect behavior or unmet acceptance criteria.
- Security, privacy, data-loss, concurrency, or compatibility risks.
- Broken public or integration boundaries.
- Missing failure handling or regression coverage.
- Documentation and decision drift.
- Unnecessary scope or dependency expansion.

For every finding, provide severity, file and line, a concrete failure scenario, supporting evidence, and the smallest reasonable fix. Do not modify files unless explicitly asked.

End with checks run, review limitations, residual risks, and a clear statement when no findings remain.
