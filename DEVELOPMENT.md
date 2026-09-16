# Development Workflow

## Bootstrap the Harness

1. Complete docs/project-brief.md with product outcomes and constraints.
2. Inspect the repository before editing ARCHITECTURE.md.
3. Configure the command variables in Makefile from commands the project already uses.
4. Replace the starter entries in ROADMAP.md and TASKS.md.
5. Keep only the prompt modes useful to the team.

Do not use the harness to choose a language, framework, package manager, storage system, deployment platform, or testing stack.

## Discover Project Commands

Look for existing manifests, lockfiles, CI workflows, scripts, and contributor documentation. Verify commands locally before recording them. Then configure:

- DEV_CMD
- FORMAT_CMD
- LINT_CMD
- TYPECHECK_CMD
- TEST_CMD
- BUILD_CMD
- INTEGRATION_CMD

The variables may be set in the project Makefile or supplied by the environment. Unconfigured commands fail when called directly; make check skips them with an explicit message so a new scaffold can still validate its harness.

## Browser Validation

The project-scoped Codex configuration registers the Playwright MCP server as playwright. It requires Node.js 20 or newer and npx. Run make mcp-check after setup; restart Codex after changing the MCP configuration so the server is discovered.

When browser-based validation is applicable, use the playwright MCP server for rendering, responsive behavior, keyboard and accessibility flows, network states, downloads, and screenshots. Record the scenarios and observed results in docs/verification-checklist.md or the relevant task.

## Task Loop

Use one TASKS.md item at a time:

1. Confirm its acceptance criteria and dependencies.
2. Use prompts/plan.md for bounded planning.
3. Use prompts/architect.md if a material decision is unresolved.
4. Use prompts/builder.md or prompts/implement.md after required ADRs are accepted.
5. Use prompts/debug.md for a reproducible failure.
6. Use prompts/review.md for a read-only diff review.
7. Run the configured checks and update the task evidence.

## Validation

    make help
    make check
    git diff --check

Add project-specific build, test, integration, packaging, or deployment checks to docs/verification-checklist.md. Preserve exact commands and results in the handoff.
