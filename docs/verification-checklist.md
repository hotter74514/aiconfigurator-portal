# Verification Checklist

Customize this checklist for the project's actual delivery path. Remove non-applicable items with a short reason and add exact commands as the toolchain becomes known.

## Reproducibility

- [ ] A clean checkout can be set up using documented commands.
- [ ] Required tools, versions, configuration, and safe example values are documented.
- [ ] No credentials, private data, generated output, or local-only state are committed.

## Automated Checks

- [ ] Formatting check passes, when configured.
- [ ] Linting and static analysis pass, when configured.
- [ ] Type checking passes, when configured.
- [ ] Unit and integration tests pass, when configured.
- [ ] Build or packaging checks pass, when configured.
- [ ] git diff --check passes.

## Primary Outcome

- [ ] The shortest end-to-end user or caller path succeeds.
- [ ] Its observable output satisfies docs/project-brief.md.
- [ ] At least one important invalid-input or dependency-failure path is verified.
- [ ] Real integrations are distinguished clearly from test doubles.

## Quality and Operations

- [ ] Relevant security, privacy, accessibility, performance, compatibility, and operability expectations are verified.
- [ ] Failure messages contain enough context for diagnosis without exposing sensitive information.
- [ ] Recovery, rollback, or cleanup behavior is understood where relevant.

## Handoff Evidence

- [ ] Exact commands and results are recorded.
- [ ] Changed behavior and files are summarized.
- [ ] Assumptions, known limitations, unverified areas, and follow-up work are explicit.
- [ ] ROADMAP.md, TASKS.md, ARCHITECTURE.md, and accepted ADRs match the resulting system.
