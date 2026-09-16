# Project Engineering Harness

This repository includes a project-agnostic harness for AI-assisted software engineering. The harness defines how to discover project context, plan work, surface architecture choices, implement small changes, verify outcomes, and hand work off without prescribing an application stack or system design.

## What the Harness Provides

- AGENTS.md: repository-wide operating rules and safety boundaries.
- docs/project-brief.md: product goals, constraints, and acceptance criteria.
- ARCHITECTURE.md: an evidence-based system map populated from the actual project.
- docs/DESIGN_DECISIONS.md and docs/decisions/: decision log and ADR template.
- ROADMAP.md and TASKS.md: outcome sequencing and executable work items.
- prompts/: focused architect, planner, builder, debugger, and reviewer modes.
- Makefile: stable entry points whose underlying project commands are configured explicitly.
- .codex/config.toml: conservative project-scoped Codex defaults.

The harness intentionally contains no decisions about language, framework, storage, API style, deployment platform, or infrastructure. Those choices must come from project evidence and approved ADRs.

## Adopt It in a Project

1. Replace the placeholders in docs/project-brief.md.
2. Inspect the existing repository and record only verified facts in ARCHITECTURE.md.
3. Configure the command variables at the top of Makefile using the project's existing toolchain.
4. Replace the starter roadmap and task queue with work derived from the brief.
5. Create an ADR from docs/decisions/000-template.md only when a material decision is actually required.
6. Run make check and execute the project-specific verification checklist before handoff.

## Working Loop

Start with docs/project-brief.md, then read AGENTS.md, ARCHITECTURE.md, ROADMAP.md, and TASKS.md. Use the prompt matching the current activity. Keep each change small, test observable behavior, update documentation when facts change, and report commands exactly as run.

    make help
    make check

See DEVELOPMENT.md for setup and customization guidance.
