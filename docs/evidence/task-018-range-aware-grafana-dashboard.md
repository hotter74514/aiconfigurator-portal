# TASK-018 Evidence: Range-Aware Portal Status Dashboard

## Scope

The dashboard remains an additive Grafana artifact. It keeps the existing
Prometheus datasource and metric families, but makes selected-range behavior
explicit:

- completed, failed, and rejected cards round Prometheus counter increases to
  user-facing whole-run counts;
- rate, error, and cache panels use a five-minute rate window, which is compatible
  with the deployed Prometheus target's one-minute scrape interval, and return zero
  during quiet periods instead of an empty vector;
- run and HTTP quantiles use the selected dashboard range; and
- the instance variable only lists series carrying the portal pod label.

## Checks executed

| Check | Result |
|---|---|
| `uv run pytest tests/test_grafana_dashboard.py -q` | Passed: 3 tests. |
| `make check` | Passed: Ruff, mypy, 43 Python tests, and 4 client tests. Two existing dependency deprecation warnings were emitted by the test run. |
| `jq empty deploy/observability/grafana/dashboards/portal-status.json` | Passed. |
| `kubectl apply --dry-run=client -k deploy/observability` | Passed. |
| `git diff --check` | Passed. |
| Prometheus API validation | Passed: all 24 dashboard targets returned `status=success` with `$instance` and `$__range` resolved to `.*` and `3h`; rate targets use the checked-in `[5m]` window. |

## Minikube deployment

The updated JSON was imported into the existing `observability/grafana` service
through the authenticated Grafana API. Grafana returned:

```text
uid=serving-configuration-portal-status
version=4
status=success
```

The repository's `deploy/observability` bundle emits dashboard ConfigMaps but does
not own the separately installed Grafana Helm deployment. Applying that bundle
without mounting its ConfigMaps would create resources in the default namespace
and would not load the dashboard into this Grafana instance. The temporary
standalone Alloy resources created by that validation apply were removed; the
existing observability stack and portal pod were left running.

## Browser validation

Playwright MCP opened the deployed dashboard with `from=now-3h&to=now` and observed:

- Portal availability: `Available`.
- Active runs: `0`; queued runs: `0`.
- Completed runs: `11`; failed and rejected runs: `0`.
- Run outcomes: quiet-period values rendered as `0 rd/m`.
- Run duration: p50 `4.38 s`, p95 `9.63 s`, last run `6.44 s`.
- The HTTP request-rate query executed with `[5m]`; Prometheus returned a non-zero
  `/api/runs` rate around the 21:55 request burst. The prior `[1m]` query returned
  no samples because the deployed target scrapes every one minute.

The only browser console error was Grafana's built-in request for
`/api/dashboards/uid/serving-configuration-portal-status/public-dashboards`, which
returned 404 because public dashboards are disabled in this local Grafana. Panel
data loaded successfully.
