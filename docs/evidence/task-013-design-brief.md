# TASK-013 Stage 11 — Precision planning workspace brief

## Source and boundary

- Frontend design guidance: Anthropic `frontend-design` skill from
  `anthropics/claude-code` commit `68ac8bbf0245b615b41517bf8f2b2f35af1ae31d`.
- No runtime dependency is shipped from that skill. The portal remains FastAPI,
  Jinja2, native JavaScript, and static CSS.
- Post-implementation audit reference: Vercel `web-interface-guidelines`
  `command.md` at commit `e3d624baaf29dc1fc645aff3e38f03e564d2d6b1`.

## Design direction

The portal is a calm, high-density engineering console for choosing an LLM serving
configuration worth benchmarking. It is not a marketing dashboard. The primary
sequence is visible as three actions: define workload, observe the run, compare and
export.

### Token choices

| Concern | Decision |
|---|---|
| Canvas | `#edf1ef` cool grey-green workbench with a restrained grid texture |
| Surfaces | Near-white panels with thin cool-grey rules and low-elevation shadow |
| Action | Copper orange `#bd5d2d`, used for the one primary estimate action and warning edge |
| Status | Teal success `#237268`, amber queue `#9a691d`, red failure `#a24642`; every state also has text |
| Type | System sans for prose and controls; system monospace for metric values and operational labels |
| Shape | Small radius for controls, moderate radius for grouped panels; no decorative pill-card repetition |

### Layout concept

```text
┌──────────────────────────────────────────────────────────────┐
│ console label / title / purpose                         mark │
├──────────────────────────────────────────────────────────────┤
│ estimate warning                                             │
├──────────────────────────────┬───────────────────────────────┤
│ 01 Configuration inputs      │ 02 Run status                  │
│ model                        │ shared capacity                │
│ GPU / targets / tokens       │ browser-local history          │
│ [Estimate configurations]    │                               │
├──────────────────────────────┴───────────────────────────────┤
│ 03 Ranked results / comparison / Pareto / artifact download   │
└──────────────────────────────────────────────────────────────┘
```

Desktop gives the configuration form the largest column and keeps run state in a
quiet side stack. At 780px the side stack becomes a compact two-column region; at
520px all content becomes one column and data tables retain exact values in local
horizontal scroll containers. Text is left aligned, numerals use tabular treatment,
and the primary action remains the strongest visual accent.

## Baseline state matrix

Before the refresh, Playwright MCP captured the ready state at 1440×900 and 390×844.
The unstyled page was a full-width document flow: the form consumed most of the
vertical page, status/capacity/history had no visual grouping, and results had no
hierarchy beyond native table markup. Baseline narrow layout had no horizontal
overflow (`scrollWidth === 390`) but did not establish a deliberate responsive shell.

| State | Required meaning | Presentation treatment |
|---|---|---|
| Ready / empty history | Inputs can be submitted; no saved browser runs | Clear first action, status panel, empty history copy |
| Queued / running | Sweep accepted and still executing | Status text plus amber state attribute; submit disabled |
| Completed | Exact estimates, comparison, visualization, ZIP are available | Result workspace, ranked table, comparison warning, prominent download |
| Failed | Sanitized actionable failure | Red status text and alert copy; form becomes usable again |
| Capacity open/full/unavailable | Anonymous shared pressure only | Textual capacity message plus state styling; no identity or reservation claim |
| Visualization fallback | PNG missing/unavailable | Hide broken image and retain exact-value table/fallback caption |
| History populated/clear | Browser-local convenience only | Compact list, caveat copy, clear action; no server enumeration |
| Narrow / zoom / reduced motion | Same semantics at constrained presentation | One-column flow, local table scroll, visible focus, reduced-motion media rule |

## Stable behavior hooks

The following IDs and contracts remain unchanged for `portal.mjs`: `run-form`,
`submit`, `status`, `error`, `capacity`, `results`, `comparison`,
`comparison-rows`, `visualization`, `visualization-image`, `result-rows`,
`download`, `history-list`, `history-empty`, and `clear-history`. No API payload,
poll interval, cache, localStorage key, run ownership boundary, or download route
changed.
