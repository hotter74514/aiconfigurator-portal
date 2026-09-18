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

## Remaining verification

The Minikube deployment below verifies a real spawned worker exporting to an OTLP
receiver, pod stdout ingestion and structured metadata queries in Loki, Prometheus
scraping, and Grafana datasource-proxy correlation. The following gates remain
intentionally open:

- visible Playwright MCP navigation from Tempo **Logs for this span** to Loki and
  Loki **View Trace** back to the exact Tempo trace;
- Alloy/backend outage timing under the declared resource limits.

Backend URLs, tenant headers, TLS material, and credentials remain deployment inputs
and are not committed.

## Minikube deployment verification

Date: 2026-09-18 (Asia/Taipei)

The active Kubernetes context was `aiconfigurator`, backed by Minikube profile
`aiconfigurator`, with one arm64 node. The existing `observability` namespace had
healthy Alloy v1.19.2, Grafana 12.3.1, Loki 3.6.11, Tempo, Prometheus, and an OTLP
collector. The cluster's Alloy tails pod files and forwards logs to Loki; its OTLP
collector receives application traces and forwards them to Tempo.

Commands and observations:

| Command / action | Observation |
|---|---|
| `docker build --platform linux/arm64 -t serving-configuration-portal:local .` | Built the current image with the OpenTelemetry dependencies. |
| `minikube image load serving-configuration-portal:local --profile aiconfigurator` | Loaded the arm64 image into the active Minikube node. |
| `kubectl apply -f deploy/portal.yaml` | Updated the portal Deployment and Prometheus scrape annotations. |
| `kubectl -n default set env deployment/serving-configuration-portal OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317 OTEL_EXPORTER_OTLP_INSECURE=true` | Pointed this cluster's portal pod at its existing OTLP collector; rollout completed successfully. |
| `curl /health/live`, `curl /health/ready` | Both returned `{"status":"ok"}`. |
| POST `/api/runs` with `traceparent: 00-4f8f0e4c9a7b6d5c3e2f1a0b9c8d7e6f-1122334455667788-01` | Returned `202`, run `071bd0ebb6384e18b4f44f2c5a5a3b74`; the real AIConfigurator 0.11.0 run completed successfully in about 7 seconds. |
| `GET /api/runs/071bd0ebb6384e18b4f44f2c5a5a3b74` | Returned `completed`, six ranked rows, comparison data, and a verified Pareto PNG. |
| `GET http://127.0.0.1:13200/api/traces/4f8f0e4c9a7b6d5c3e2f1a0b9c8d7e6f` | Tempo returned two resource batches and spans `POST /api/runs`, `portal.run.submit`, `portal.run.execute`, and `portal.run_completed`, all sharing the requested trace ID. |
| Grafana Tempo datasource proxy for the same trace | Grafana's `tempo` datasource proxy returned the same four spans. |
| Loki query `{service_name="serving-configuration-portal"} \| trace_id = "4f8f0e4c9a7b6d5c3e2f1a0b9c8d7e6f"` | Direct Loki and Grafana's `loki` datasource proxy each returned 26 entries and lifecycle events `run_accepted`, `run_started`, and `run_completed`. |
| `GET /loki/api/v1/labels` and `/series` | Indexed labels contain service/container/namespace/job/stream metadata but no `trace_id`, `span_id`, or `run_id`; trace IDs are searchable structured metadata. |
| Prometheus `/api/v1/targets` and `/api/v1/query?query=portal_runs_submitted_total` | Portal `/metrics` target was `up`; Prometheus returned `portal_runs_submitted_total=1`. |
| Grafana `/api/health` and datasource UID API | Grafana 12.3.1 healthy; UIDs `tempo`, `loki`, and `prometheus` resolve. Tempo has `tracesToLogsV2`; Loki has the `trace_id` derived field back to Tempo. |

The repository's Playwright MCP/browser runtime was unavailable in this session, so
the final visible **Logs for this span** and **View Trace** clicks were not exercised.
The equivalent Grafana datasource-proxy and backend queries above verify the exact
correlation inputs and outputs; UI-click evidence remains the only outstanding gate.
