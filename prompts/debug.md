# Debug a Failure

Investigate a reproducible failure in this repository.

Read AGENTS.md, the relevant task and accepted ADRs, and the affected implementation and tests. Begin with the narrowest command that reproduces the problem. Capture the exact error and relevant environment facts before changing code.

For each attempt:

1. Form one falsifiable hypothesis.
2. Gather evidence that distinguishes it from alternatives.
3. Make the smallest safe change.
4. Rerun the reproducer.
5. Run broader relevant checks after the narrow check passes.
6. Add or update a regression test when the failure exposed missing coverage.

Do not hide failures, weaken assertions, disable checks, or bundle unrelated refactors. After three materially different failed attempts, stop and report the attempts, exact errors, likely cause, and two or three reasonable next approaches.
