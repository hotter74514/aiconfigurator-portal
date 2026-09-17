# ADR-004: Aggregated and Disaggregated Result Comparison

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

The verified AIConfigurator result contains independently ranked `agg` and `disagg`
frames. The portal flattens those rows into one response and table, which makes the
two serving modes visible but does not explain their trade-offs. The comparison must
handle missing modes and metrics and must not declare a universally superior mode.

## Decision Drivers

- Give one stable definition of which rows are compared.
- Show both absolute estimates and understandable deltas.
- Preserve missing data rather than inventing values.
- Keep comparison semantics testable outside browser rendering.
- Avoid implying that estimates replace production benchmarks.

## Options Considered

### Option A: Derive the Comparison Entirely in the Browser

- **Benefits:** No API change and little backend code.
- **Costs:** Domain rules, rounding, missing-value behavior, and metric selection live
  in JavaScript and can drift from other clients.
- **Failure modes:** Wrong row selection, divide-by-zero, and inconsistent semantics.
- **Reversibility:** Easy, but creates a weak ownership boundary for domain logic.

### Option B: Return a Portal-Owned Comparison Summary

- **Benefits:** One tested server-side contract owns row selection, units, deltas,
  missing values, and source modes; browser rendering stays simple.
- **Costs:** Adds a versioned response field and a small comparison function.
- **Failure modes:** Incorrect assumptions about rank semantics or metric direction.
- **Reversibility:** The additive response field can be removed or versioned without
  changing run submission and polling.

### Option C: Run a Separate Comparison Workflow

- **Benefits:** Could optimize specifically across modes or add richer analysis.
- **Costs:** More compute, lifecycle states, artifacts, and dependency coupling for
  information already present in one result.
- **Failure modes:** Mismatched inputs or versions between two runs.
- **Reversibility:** Poor relative to the optional-feature value.

## Recommendation

Choose Option B. After verifying that rank 1 is the best row independently within
each mode, add an optional `comparison` block to completed-run responses. Compare the
rank-1 `agg` and `disagg` rows and return absolute throughput, TTFT, TPOT, GPU count,
and signed percentage deltas with documented rounding. If either mode, baseline, or
required metric is unavailable, return an explicit unavailable reason. Present the
trade-offs side by side and never emit a generic winner.

## Consequences

- **Positive:** Comparison meaning is stable, reusable, and directly unit-testable.
- **Positive:** Missing and zero values have one explicit behavior.
- **Negative:** The status response gains a portal-owned derived representation.
- **Negative:** Rank semantics must be reverified when the adapter contract changes.

## Validation

1. Capture fixtures with both modes, one missing mode, missing metrics, and zero
   denominators.
2. Test row selection, units, sign, deterministic rounding, and unavailable reasons.
3. Use Playwright MCP to verify side-by-side and narrow layouts, keyboard flow, exact
   values, and benchmark warning.

## What Would Change This Decision

- AIConfigurator publishes a stable native cross-mode comparison contract.
- Product requirements define another selection objective instead of per-mode rank 1.
- Comparison expands into interactive multi-row or multi-run analysis.

## Links

- Related task: TASK-008 in `TASKS.md`
- Related decision: ADR-001
