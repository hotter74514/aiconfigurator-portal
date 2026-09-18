# TASK-014 — OpenTelemetry and Alloy evidence

Date: 2026-09-18 (Asia/Taipei)

## Implemented contract

- `Telemetry` owns the SDK providers, bounded OTLP batch processor, app-local
  Prometheus reader, force-flush, idempotent shutdown, and `OTEL_SDK_DISABLED` path.
- FastAPI instrumentation emits server spans while excluding `/health/live`,
  `/health/ready`, and `/metrics`; receive/send child spans are excluded.
- JSON stdout records include valid `trace_id`, `span_id`, and sampled state only
  when an active span exists. Existing event/run/status/error fields remain safe.
- A plain W3C `traceparent` carrier is retained in each run record. Submission,
  callback, and worker tests prove the same trace ID and explicit parent links.
- Alloy keeps only `service_name` as a Loki stream label. Trace/span IDs are
  structured metadata. Grafana provisioning uses fixed UIDs `tempo`, `loki`, and
  `prometheus` with trace-to-logs and log-to-trace configuration.

## Commands and observations

| Command | Observation |
|---|---|
| `uv run pytest -q` | 34 passed, 2 upstream TestClient deprecation warnings. |
| `uv run pytest tests/test_observability.py -q` | 8 passed, including disabled SDK, FastAPI extraction/probe exclusion, callback parent reconstruction, and a real spawned-worker carrier path. |
| `uv run ruff check src tests` | Passed. |
| `uv run mypy src` | Passed; strict mode reports no issues in 10 source files. |
| `kubectl apply --dry-run=client -f deploy/portal.yaml` | Passed. |
| `kubectl kustomize deploy/observability` | Passed; generated Alloy/Grafana ConfigMaps and workload manifests. |
| `kubectl apply --dry-run=client -k deploy/observability` | Passed for ServiceAccount, RBAC, Alloy Deployment/Service, and generated ConfigMaps. |
| `docker run --rm -v "$PWD/deploy/observability:/etc/alloy:ro" grafana/alloy:v1.11.3 fmt /etc/alloy/alloy.config.alloy` | Passed; Alloy image parsed and formatted the complete configuration. |
| `docker run ... grafana/alloy:v1.11.3 run ...` outside Kubernetes | Component syntax loaded; expected discovery errors reported because no in-cluster Kubernetes API environment was present. |
| `make build` | Linux/amd64 image built successfully; locked runtime includes OpenTelemetry API/SDK, OTLP gRPC exporter, Prometheus exporter, FastAPI, and logging instrumentation. |
| `docker run ... -e OTEL_SDK_DISABLED=true ...` plus `curl /health/live` and `/health/ready` | Both probes returned `{"status":"ok"}` while remote telemetry was disabled. |

## Not yet verified

This checkout has no reachable Tempo, Loki, Prometheus, Grafana, or Kubernetes
observability workload, so the following are intentionally not claimed as passing:

- a real spawned worker exporting to an OTLP receiver and searchable in Tempo;
- pod stdout ingestion and structured metadata queries in Loki;
- remote-write samples visible in Prometheus;
- Playwright MCP navigation from Tempo **Logs for this span** to Loki and Loki
  **View Trace** back to the exact Tempo trace;
- Alloy/backend outage timing under the declared resource limits.

These are Stage 19 environment-dependent gates. Backend URLs, tenant headers, TLS
material, and credentials must be supplied by the deployment and are not committed.
