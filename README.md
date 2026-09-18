# Serving Configuration Portal

A small self-service portal for turning an LLM model, GPU budget, and latency
targets into ranked AIConfigurator serving estimates and downloadable deployment
artifacts. It does not run a GPU benchmark or deploy the generated workload.

Every result is a planning estimate. Benchmark the generated configuration on the
target hardware before production use.

## What the Portal Delivers

- An asynchronous `202` run API with opaque IDs and queued, running, completed, and
  failed states.
- Ranked aggregated and disaggregated configurations with throughput, TTFT, TPOT,
  GPU, and topology fields supplied by AIConfigurator.
- A server-owned rank-one comparison with signed deltas, without declaring a
  universal winner.
- A portal-owned latency/throughput trade-off surface from the same full SDK
  sweep, plus the AIConfigurator-generated Pareto PNG and exact-value table
  fallbacks.
- A run-scoped ZIP containing the generated deployment files.
- A TTL/count/byte-bounded process-local completed-result cache.
- Browser-local recent-run convenience history and anonymous aggregate capacity
  awareness.
- Health, readiness, Prometheus metrics, JSON logs, a non-root container, and raw
  Kubernetes manifests.
- OpenTelemetry traces and metrics with W3C propagation through queued work, plus
  Alloy/Grafana provisioning for Tempo↔Loki correlation.

## Prerequisites

The verified path uses a Linux x86-64 container because the pinned AIConfigurator
wheel is not available natively on Apple Silicon macOS.

| Tool | Verified version | Required for |
|---|---|---|
| Docker | client/server 29.4.0 | Real build and run |
| uv | 0.11.21 | Local checks and fake-adapter tests |
| Python | 3.11.14 locally; pinned 3.11 slim image | Development/runtime |
| Node.js | 26.8.1 | Browser-local history tests and Playwright MCP |
| kubectl | 1.37.0 client | Manifest validation/deployment |
| Minikube | 1.39.0 | Optional local-cluster verification |

Docker needs enough capacity for the declared two CPUs and 4 GiB memory. The release
image and checked-in manifest target x86-64. For local validation on an arm64
Minikube node, build and load an architecture-matched image as shown below rather
than relying on binfmt/qemu to select an amd64 OCI index.

## Quick Start

Build only from the committed lockfile and pinned Dockerfile inputs:

```sh
make build
```

Start the real portal:

```sh
docker run --rm --name serving-configuration-portal-demo \
  --platform linux/amd64 --cpus=2 --memory=4g \
  -p 8080:8080 serving-configuration-portal:local
```

Open <http://127.0.0.1:8080/> and submit the defaults, or use the safe documented
smoke input:

```sh
curl -sS -X POST http://127.0.0.1:8080/api/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-32B-FP8",
    "system": "h200_sxm",
    "total_gpus": 32,
    "ttft": 1000,
    "tpot": 10,
    "isl": 3000,
    "osl": 512
  }'
```

The response contains a `run_id`, `status_url`, and recommended polling interval.
Poll the returned URL until it is terminal, then download:

```text
GET /api/runs/{run_id}/artifacts
```

The verified offline smoke completed with `--network none`: AIConfigurator 0.11.0
returned six rows, one Pareto visualization, and 72 files for the documented input.
The runtime does not need network access for that case because the required model
metadata and performance data are packaged. Image build and dependency installation
do require registry/package access. Do not assume every future dependency version or
new model has the same offline behavior.

## Local Development and Checks

```sh
uv sync --frozen
make check
make integration
make mcp-check
git diff --check
```

`make check` runs Ruff, strict mypy, pytest, and the Node client tests. The local
macOS environment intentionally tests through the fake adapter; the real dependency
path runs in the Linux/amd64 image.

`make dev` starts the normal application entry point. On a host where the optional
AIConfigurator dependency is unavailable, submissions fail with a sanitized
dependency error while the page, probes, and other API endpoints remain available.

## Architecture and Data Flow

```text
browser / API client
        |
        v
FastAPI + Jinja2 + native JavaScript
        |
        +--> validation --> bounded admission (1 active + 4 queued)
        |                         |
        |                         v
        |                 isolated worker process
        |                         |
        |                         v
        |                AIConfigurator 0.11.0
        |                         |
        +<-- status/results ------+
        |                         |
        +<-- run-scoped files ----+--> bounded emptyDir / local run root

OpenTelemetry traces: FastAPI -> submit/queue callbacks -> spawned worker -> Alloy -> Tempo
JSON stdout logs:     active trace IDs ---------------------------> Alloy -> Loki
Prometheus metrics:   /metrics ----------------------------------> Alloy -> Prometheus
```

One Uvicorn worker and one Kubernetes replica are intentional. Run state, cache
entries, and artifacts are local to that process/pod. See the accepted records in
`docs/decisions/` for alternatives and decision-change conditions.

## API and Operational Signals

| Endpoint | Meaning |
|---|---|
| `POST /api/runs` | Validate and admit work; returns `202`, `429`, `503`, or validation error |
| `GET /api/runs/{id}` | Lifecycle status and completed result contract |
| `GET /api/runs/{id}/artifacts` | Completed-run ZIP; incomplete is `409` |
| `GET /api/runs/{id}/visualizations/{asset_id}` | Verified contained PNG |
| `GET /api/capacity` | Anonymous active/queued counts and admission state |
| `GET /health/live` | Web process can answer requests |
| `GET /health/ready` | Process is initialized and accepting admission |
| `GET /metrics` | Low-cardinality Prometheus metrics |

Readiness remains healthy when the bounded queue is busy. It becomes unavailable
during shutdown. Capacity information is advisory and does not reserve a slot.
Lifecycle logs are JSON and include `trace_id`/`span_id` when a span is active. The
run manager carries only W3C `traceparent` values across its queue and spawned
worker boundary. Metrics do not use run IDs, trace IDs, model names, or user-derived
labels.

## OpenTelemetry, Alloy, and Grafana

The application uses the OpenTelemetry API for traces and portal metrics while
keeping JSON logs on stdout. Configure `OTEL_EXPORTER_OTLP_ENDPOINT` (gRPC) and
`OTEL_SERVICE_NAME` in the deployment; `OTEL_SDK_DISABLED=true` leaves the business
path available without remote telemetry. Exporter queues and shutdown are bounded,
and exporter failures are not returned as API errors.

The checked-in optional collector stack is under `deploy/observability/`:

```sh
kubectl kustomize deploy/observability
kubectl apply --dry-run=client -k deploy/observability
```

Alloy receives OTLP traces, tails only portal pod logs, keeps `service_name` as a
Loki stream label, and stores `trace_id`/`span_id` as structured metadata. It
scrapes `/metrics` and forwards samples by remote write. `alloy.config.alloy`
expects deployment-supplied `TEMPO_OTLP_ENDPOINT`, `LOKI_URL`, and
`PROMETHEUS_REMOTE_WRITE_URL`; Grafana provisioning expects `TEMPO_QUERY_URL`,
`LOKI_QUERY_URL`, and `PROMETHEUS_QUERY_URL`. Credentials, tenant headers, and TLS
material are intentionally absent from the repository.

Grafana data sources use stable UIDs `tempo`, `loki`, and `prometheus`. Tempo's
`tracesToLogsV2` searches Loki by `service_name` and trace ID; Loki's `trace_id`
derived field links back to the exact Tempo trace. A real Tempo/Loki/Prometheus/
Grafana deployment is required to verify the clickable links; local repository
checks validate the application path and configuration shape only.

The same observability bundle provisions the `Serving Configuration Portal Status`
dashboard (UID `serving-configuration-portal-status`) from
`deploy/observability/grafana/dashboards/portal-status.json`. It uses only the
existing `prometheus` datasource and an `instance` selector, so it works with
both direct Kubernetes scraping and the Alloy remote-write path. The panels cover
availability, active/queued saturation, completed/failed/rejected outcomes, run
and HTTP latency, request/error rate, and cache activity/hit ratio. The dashboard
provider and JSON are emitted as `portal-grafana-dashboard-provider` and
`portal-grafana-dashboards` ConfigMaps by Kustomize. Mount those ConfigMaps in the
Grafana namespace at `/etc/grafana/provisioning/dashboards/dashboards.yaml` and
`/var/lib/grafana/dashboards/portal/` respectively (the repository intentionally
does not own the separately deployed Grafana workload).

## Cache, History, and Retention

Completed bundles are cached only in process memory for exact canonical request and
version namespaces. Defaults are a one-hour TTL, 32 entries, and 64 MiB of ZIP bytes.
A hit receives a fresh run ID. Failures and in-flight requests are not cached, and
all cache state disappears on restart.

The browser keeps at most 20 run summaries in `localStorage` and revalidates their
opaque IDs. This is convenience history, not an account, authorization boundary,
privacy boundary, audit log, or durable/cross-device history. Anyone sharing the
browser profile can see it. Site-data clearing, one-hour server retention, or a
portal restart can remove access to those runs.

## Kubernetes

Validate without changing resources:

```sh
kubectl apply --dry-run=client -f deploy/portal.yaml
```

Deploy to an x86-64 cluster where `serving-configuration-portal:local` is available:

```sh
kubectl apply -f deploy/portal.yaml
kubectl rollout status deployment/serving-configuration-portal --timeout=180s
kubectl port-forward service/serving-configuration-portal 8080:80
```

For local-only validation on an arm64 Minikube profile, keep the amd64 release image
and manifest unchanged and override only the live Deployment:

```sh
docker buildx build --platform linux/arm64 --load \
  -t serving-configuration-portal:local-arm64 .
minikube image load serving-configuration-portal:local-arm64 \
  --profile aiconfigurator
kubectl set image deployment/serving-configuration-portal \
  portal=serving-configuration-portal:local-arm64
kubectl rollout status deployment/serving-configuration-portal --timeout=180s
```

The manifest uses one `Recreate` replica, non-root UID/GID 10001, a read-only root
filesystem, dropped capabilities, runtime-default seccomp, startup/live/ready
probes, two CPU/4 GiB requests and limits, a 1 GiB run `emptyDir`, and a 256 MiB
temporary `emptyDir`. Generated serving manifests are downloads only; the portal
never applies them to Kubernetes.

## Design Discussion Areas

1. **User workflow:** one page covers request, progress, comparison, exact results,
   visualization, and artifact download.
2. **Dependency boundary:** a typed adapter contains the pinned SDK and normalized
   portal-owned result contract.
3. **Execution model:** immediate `202` plus polling avoids holding a request open;
   CPU work runs in one isolated process.
4. **Concurrency:** one active and four queued requests bound CPU and memory; excess
   work gets retryable `429`.
5. **Ranking and SLA:** the SDK performs strict SLA filtering and independently
   ranks aggregated and disaggregated modes.
6. **Artifacts and storage:** server-generated opaque IDs and contained paths scope
   downloads to one ephemeral run root.
7. **Resilience:** timeout, sanitized failure, graceful shutdown, TTL cleanup, and
   startup orphan cleanup are explicit; restart recovery is deliberately absent.
8. **Observability:** live/ready/capacity endpoints, structured logs, and bounded
   metrics distinguish health, saturation, and failure.
9. **Deployment and security:** a pinned non-root image and restrictive single-pod
   manifest keep the take-home deployment inspectable; no shell evaluates input.
10. **Evolution:** durable metadata/object storage and a dedicated queue/worker are
    required before multiple replicas, private ownership, quotas, or durable history.

## Fifteen-Minute Demo

1. Build and start the image with the Quick Start commands; show `/health/live`,
   `/health/ready`, `/api/capacity`, and `/metrics`.
2. Open the page and call out the estimate/benchmark warning and default Qwen/H200
   request.
3. Submit once, show the opaque run ID and running state, then inspect the ranked
   rows, agg/disagg comparison, portal-owned Pareto trade-off surface, and same-run
   SDK image fallback.
4. Download the ZIP and list its generated CSV, YAML, JSON, shell, and image files.
5. Submit the identical request again; show the fresh run ID and cache hit metric.
6. Demonstrate a deliberate validation failure with an unsupported system and show
   that no run is admitted.
7. Show JSON logs, low-cardinality metrics, the one-replica Kubernetes shape, probe
   semantics, `emptyDir` limits, and restrictive security context.
8. Close with the limitations below and the migration triggers in the ADRs.

## Known Limitations

- No authentication, authorization, private ownership, per-team quota, fairness, or
  audit trail exists. Add identity at the HTTP boundary and persist owner IDs with
  metadata before exposing private multi-user history or downloads.
- A restart or pod replacement loses active/queued metadata, cache state, and all
  `emptyDir` artifacts. Old status/download URLs return `404`.
- Only one replica and one active sweep are supported; this is not highly available.
- Timeouts mark a run failed but cannot guarantee immediate termination of native
  dependency work already executing in the worker process.
- Generated configurations use the dependency's default mapping. The verified run
  searched performance DB `1.3.0rc10` and generated the default TRT-LLM mapping for
  `1.3.0rc14`; validate target-version compatibility before deployment.
- The portal-owned trade-off surface is limited to request latency versus cluster
  throughput and the bounded complete frontiers exposed by AIConfigurator. The
  dependency-generated PNG remains non-interactive; the exact-value result table
  remains the authoritative numeric fallback.
- Local browser history is visible to anyone using the same browser profile.
- TLS, production secrets management, autoscaling, durable queues/storage, and real
  GPU benchmark feedback are outside this repository's scope. The optional
  observability stack still requires deployment-specific backend URLs and secrets.

## Evidence and Decisions

- `docs/verification-checklist.md` is the granular acceptance index.
- `docs/evidence/` records exact commands and observed results.
- `docs/DESIGN_DECISIONS.md` indexes ADR-001 through ADR-009.
- `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, and `IMPLEMENTATION_PLAN.md` describe
  the system boundary and staged delivery history.
