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

## Verification scope

The Minikube deployment below verifies a real spawned worker exporting to an OTLP
receiver, pod stdout ingestion and structured metadata queries in Loki, Prometheus
scraping, Grafana datasource-proxy correlation, outage isolation, graceful
shutdown, recovery, and negative propagation behavior.

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

## Playwright MCP Grafana navigation

The project-scoped Playwright MCP was used against the port-forwarded Grafana UI
(`http://127.0.0.1:13000/`) with the real trace ID
`4f8f0e4c9a7b6d5c3e2f1a0b9c8d7e6f`:

1. Grafana Explore → Tempo accepted the trace ID and rendered
   `serving-configuration-portal: POST /api/runs` with four spans, including
   `portal.run.submit`, `portal.run.execute`, and `portal.run_completed`.
2. On the root span, **Explore the logs for this in split view** opened Loki with
   the correlated time window and trace/span filters. The Loki result displayed
   JSON records containing the same trace ID, including `run_started`.
3. Opening a Loki record exposed the derived-field **View trace** action. Clicking
   it opened a Tempo pane whose query and rendered trace both contained the exact
   original trace ID.

This proves both visible Grafana navigation directions for the same real run. The
following outage and negative-propagation exercises close the remaining Stage 19
gates.

## Outage and negative-propagation evidence

Each outage was applied to the existing Minikube stack, exercised with a fresh
uncached AIConfigurator request, and restored before the next case. Portal pod
memory stayed below the 4 GiB container limit; the application continued to serve
probes and business traffic while telemetry destinations retried asynchronously.

| Failure exercise | Observation while unavailable | Recovery |
|---|---|---|
| OTLP collector scaled to zero | Live/readiness returned 200; run `dda4423b268d4f1dbae5d56be59d49a5` completed. Submit returned in 15 ms, terminal state arrived after 12 s, memory was 551,669,760 bytes, and stdout retained the trace-correlated lifecycle records. OTLP exporter emitted bounded retry/error messages. | Collector restored to one Ready pod. |
| Loki StatefulSet scaled to zero | Live/readiness returned 200; run `7959531b295245cdb9d6d7f90d18c9f1` completed after four polling seconds. Stdout retained 20 records for the trace and portal memory was 549,392,384 bytes; Alloy reported destination errors without affecting the request. | Loki restored to `2/2` containers Ready. |
| Tempo StatefulSet scaled to zero | Live/readiness returned 200; run `712252da8f8040dbaace6b99257505b` completed after four polling seconds, memory 555,429,888 bytes. Collector retry logs showed connection-refused delivery failures only. | Tempo restored to one Ready pod. |
| Prometheus deployment scaled to zero | Live/readiness and the portal `/metrics` endpoint remained available; run `075ca8db974e4375a7aab5550cf59b5e` completed after four polling seconds, memory 530,509,824 bytes. Alloy remote-write errors were asynchronous. | Prometheus restored to `2/2` containers Ready. |
| Alloy DaemonSet made unschedulable | Live/readiness and `/metrics` remained available; run `b5f9c860004a4ec3a4612a9e69b8cb87` completed after four polling seconds, memory 533,782,528 bytes, and stdout retained 20 trace-correlated records. | Alloy node selector reverted; one Available pod returned. |
| Grafana deployment scaled to zero | Live/readiness returned 200; run `f860d26d7983481c9ea911e0eae13b68` completed after eight polling seconds. | Grafana restored to one Available pod. |
| Portal pod deletion / shutdown | Existing pod terminated in approximately 3 seconds, so telemetry shutdown/flush did not hold the 30-second grace period. Kubernetes emitted one transient `Insufficient memory` scheduling event while all observability pods were restored; the replacement then became Ready and probes returned 200. | Replacement pod `serving-configuration-portal-768c749689-cj4c2` running. |

After all components were restored, recovery run `5c3869e9c35f46d2b2dfad50efcea349`
with trace ID `deadbeefdeadbeefdeadbeefdeadbeef` completed. Tempo returned HTTP 200
with four spans, Loki returned HTTP 200 with 20 matching entries, stdout retained
20 matching records, and all observability pods were Ready.

Propagation edge cases were also exercised: malformed, absent, and unsampled
`traceparent` requests all returned 202 and completed. The malformed case created
no Loki trace entry; the unsampled case retained 20 Loki records with its trace ID
but Tempo correctly returned 404 because an unsampled trace is not stored.
