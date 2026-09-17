# TASK-013 — UI refresh evidence

## Scope and implementation

The portal now presents a responsive precision-planning workspace while retaining
the FastAPI/Jinja2/native-JavaScript boundary. Changed UI files are:

- `src/portal/templates/index.html` — semantic workspace shell, stable hooks,
  accessible captions, skip link, and persistent estimate/capacity/history warnings.
- `src/portal/static/portal.css` — dedicated tokenized visual layer, responsive
  layout, form/table/focus states, reduced-motion and forced-colors handling.
- `src/portal/static/portal.mjs` — presentation-only `data-state` attributes for
  queued/running/completed/failed, capacity, and visualization fallback.
- `tests/test_app.py` — static stylesheet delivery and stable DOM hook assertions.

The visual direction and complete state matrix are recorded in
`docs/evidence/task-013-design-brief.md`.

## Pinned guidance

- `frontend-design`: `anthropics/claude-code` commit
  `68ac8bbf0245b615b41517bf8f2b2f35af1ae31d`; installed in personal Codex scope at
  `/Users/sean_yang/.codex/skills/frontend-design`.
- `web-interface-guidelines`: `vercel-labs/web-interface-guidelines` commit
  `e3d624baaf29dc1fc645aff3e38f03e564d2d6b1`; its upstream `command.md` was used
  as the post-implementation audit reference. Neither source is a shipped runtime
  dependency.

## Exact checks and observations

### Automated

```text
make check
```

Result: Ruff passed, mypy passed for 10 source files, 26 pytest tests passed, and
3 Node history tests passed (only existing Starlette/httpx deprecation warnings).

```text
git diff --check
```

Result: passed with no whitespace errors.

The integration template test also confirms `/static/portal.css` is delivered,
the stable form/result hooks remain present, and required estimate/capacity/history
copy is preserved.

### Playwright MCP browser evidence

The project-scoped Playwright MCP server from `.codex/config.toml` was used with its
isolated profile. Captures are stored beside this report:

- `before-ready-1440x900.png`, `before-ready-390x844.png` — pre-refresh baseline.
- `after-ready-1440x900.png`, `after-ready-390x844.png` — ready state after refresh.
- `after-ready-320x700-reduced-motion.png` — narrow and reduced-motion check.
- `after-completed-1440x900.png` — completed result with comparison, Pareto image,
  ranked rows, browser history, and download action.
- `after-failed-saturated-1440x900.png` — failed run and actionable sanitized error.
- `after-visualization-fallback-1440x900.png` — missing-image fallback with exact
  result table retained.
- `final-ready-1440x900.png`, `final-ready-390x844.png` — final captures after the
  guideline-audit fixes (skip link, image dimensions, touch behavior, heading wrap).

Observed results:

| Scenario | Observation |
|---|---|
| 1440px ready | Configuration is the dominant column; status, shared capacity, and browser history form a readable side stack |
| 390px ready | One-column flow; form controls and action remain usable; `scrollWidth === 390` |
| 320px + reduced motion | `scrollWidth === 320`; `matchMedia('(prefers-reduced-motion: reduce)').matches === true` |
| Keyboard | First eight Tab stops were `model`, `system`, `total_gpus`, `ttft`, `tpot`, `isl`, `osl`, `submit`; skip link is available before them |
| Completed | Results visible, 2 ranked rows rendered, comparison visible, Pareto image visible, download visible, 1 browser-history entry recorded |
| Download | Playwright download event completed with suggested filename `run-artifacts.zip` and no download failure |
| Failed | Status state `failed`; form re-enabled; sanitized error text remains in the alert region |
| Saturated | Capacity text: `Shared capacity is full: 1 run active; 4 waiting. New submissions may be rejected; retry later.` and panel state `full` |
| Visualization fallback | Visualization section remains visible, image is hidden after 404, `data-state="fallback"`, ranked table remains visible |
| History clear | List count changed from 2 to 0, empty message became visible, localStorage key became `null` |
| Zoom | A two-times CSS scale smoke check retained `scrollWidth === viewport`; browser zoom hotkeys were also exercised through Playwright MCP |

The final browser pass confirmed `skipLink === true`, initial visualization
dimensions `[1, 1]`, desktop `scrollWidth === 1440`, and narrow `scrollWidth === 390`.

The completed/failure/capacity fixtures above are deterministic browser route
fixtures. They validate presentation and state handling, not real AIConfigurator
execution; the real container/SDK flow remains covered by the prior TASK-012 and
TASK-001 evidence.

### Container smoke

```text
make build
docker run -d --name task013-portal -p 18080:8080 serving-configuration-portal:local
curl -fsS http://127.0.0.1:18080/health/live
curl -fsSI http://127.0.0.1:18080/static/portal.css
docker stop task013-portal
docker rm task013-portal
```

Result: the pinned `linux/amd64` image built successfully; the emulated local
container returned `{"status":"ok"}` and served the stylesheet with HTTP 200 and
`content-type: text/css; charset=utf-8`. The temporary test container was stopped
and removed after verification.

## Audit findings resolved

The guideline audit found and addressed: skip navigation link, explicit image
`width`/`height` plus lazy loading, balanced heading wrapping, `touch-action:
manipulation`, visible `:focus-visible` rings, semantic controls, non-color status
copy, reduced-motion handling, and table numeric treatment. No `transition: all`,
zoom-disabling viewport directive, external font, runtime CDN, or icon-only
unlabelled action was introduced.

## Limitations and rollback

- The generated Pareto PNG retains its dependency-provided visual style; the exact
  value ranked table remains the accessible fallback.
- Browser screenshots use deterministic route fixtures for presentation states; no
  production API or data is represented by those fixtures.
- Rollback is a focused revert of the UI refresh commit; the API, run manager,
  cache, storage, and adapter boundaries are unchanged.
