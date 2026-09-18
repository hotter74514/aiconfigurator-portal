# TASK-016 Evidence: Portal Status Grafana Dashboard

## Scope

The dashboard is an additive Grafana file-provisioning artifact. It reuses the
existing `prometheus` datasource UID and the portal's low-cardinality metrics; it
does not add instrumentation, alerts, credentials, or a new backend.

## Checks executed

On the local checkout and Minikube observability stack:

| Check | Result |
|---|---|
| `uv run pytest tests/test_grafana_dashboard.py` | Passed: 3 tests; JSON contract, existing metric names, stable datasource UID, and Kustomize references are covered. |
| `jq empty deploy/observability/grafana/dashboards/portal-status.json` | Passed. |
| `kubectl kustomize deploy/observability` | Passed; rendered provider, dashboard, and datasource ConfigMaps. |
| `kubectl apply --dry-run=client -k deploy/observability` | Passed; all generated resources validated client-side. |
| Prometheus API instant queries for every dashboard target | Passed; all 24 expressions returned API `status=success` after replacing Grafana variables with `.*`, `6h`, and `5m` for the check. |
| Grafana `/api/health` | Passed; Grafana `12.3.1`, database `ok`. |
| Grafana dashboard API import | Passed; UID `serving-configuration-portal-status`, version `2` after the final submitted-rate target was added. |

## Browser validation

Playwright MCP opened the dashboard at the local Grafana port-forward and waited
for all panels to render. The page showed:

- Portal availability: `Available`.
- Active runs: `0`; queued runs: `0`.
- Completed runs: `16.7` over the selected six-hour window; failed and rejected
  runs: `0`.
- Run outcomes and work saturation panels. The outcome rate showed `No data` after
  the last run aged beyond the selected rate interval, which is the expected
  Prometheus behavior; the panel remains available for the next run.
- Run duration with the last observed run around `15.3 s`.
- HTTP request rate by normalized route, 4xx/5xx error rate, and p50/p95 latency.
- Cache hit ratio: `12.2%` in the observed six-hour window.

Prometheus-backed panel requests returned HTTP 200. The only browser console error
was Grafana's built-in request to
`/api/dashboards/uid/serving-configuration-portal-status/public-dashboards`, which
returned 404 because public dashboards are not enabled in this local Grafana
deployment; it is unrelated to panel data or dashboard provisioning.

## Provisioning limitation

The repository emits the provider and dashboard ConfigMaps but does not own the
separately installed Grafana Helm release. Operators must mount those ConfigMaps
in the Grafana namespace as documented in `README.md`; the local UI check imported
the same JSON through Grafana's API to validate the dashboard schema and queries.
