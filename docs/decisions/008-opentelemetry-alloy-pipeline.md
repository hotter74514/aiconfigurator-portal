# ADR-008: OpenTelemetry and Grafana Alloy Telemetry Pipeline

## Status

**Accepted**

## Decision Owner

Repository owner / take-home candidate.

## Context

The portal currently exposes custom `prometheus_client` metrics and emits structured
JSON logs, but it does not emit distributed traces or correlate logs with trace
context. A run begins in a FastAPI request, may wait in the in-process queue, and
then executes AIConfigurator in a `ProcessPoolExecutor` child process after the
originating HTTP request has returned. Framework-only HTTP instrumentation therefore
cannot prove end-to-end propagation through the complete run lifecycle.

Operators need OpenTelemetry-based telemetry with these destinations:

- application logs collected by Grafana Alloy and written to Loki;
- traces exported through Alloy to Tempo;
- metrics delivered to Prometheus; and
- bidirectional Grafana navigation from a Tempo trace to its Loki logs and from a
  Loki log record back to the same Tempo trace.

The solution must preserve the existing `/metrics` operational contract, keep
telemetry failures outside the business request failure path, avoid high-cardinality
metric and Loki stream labels, and not expose request bodies, generated artifacts,
credentials, or arbitrary client baggage.

## Decision Drivers

- Preserve one trace across the FastAPI request, queued work, callback threads, and
  isolated worker process.
- Reuse supported instrumentation for FastAPI and Python logging while keeping
  application-specific run lifecycle spans explicit and testable.
- Keep logs available on stdout when Alloy or Loki is unavailable.
- Preserve Prometheus pull semantics and the existing `/metrics` endpoint.
- Make Tempo-to-Loki and Loki-to-Tempo navigation deterministic and provisioned as
  code rather than an undocumented Grafana UI setting.
- Keep telemetry queues, labels, attributes, retries, and shutdown behavior bounded.
- Preserve the single-pod application architecture and avoid embedding backend
  credentials in the repository.

## Options Considered

### Option A: Hybrid OpenTelemetry Instrumentation with Alloy Routing

- **Benefits:** Uses stable OpenTelemetry trace and metric APIs; retains reliable
  stdout logs; preserves `/metrics`; uses official FastAPI and logging
  instrumentation; permits explicit process-boundary propagation; and allows Alloy
  to route each signal to its native backend.
- **Costs:** Requires both OTLP and Prometheus collection paths, explicit worker
  initialization, Grafana data-source provisioning, and cross-process integration
  tests.
- **Failure modes:** Incorrect carrier serialization can split a trace; duplicate
  instrumentation can create duplicate spans; mismatched Grafana data-source UIDs or
  fields can break navigation; an unbounded exporter can consume resources during a
  backend outage.
- **Operability:** Application logs remain inspectable from container stdout. Alloy
  owns backend delivery, retry, batching, and destination configuration.
- **Testability:** In-memory exporters cover process-local behavior; a local OTLP
  receiver and real spawned worker prove the process boundary; Grafana UI checks
  prove the user-visible correlations.
- **Security:** Only allowlisted attributes are emitted. Trace IDs and run IDs are
  searchable fields, not indexed high-cardinality metric or Loki stream labels.
- **Reversibility:** High. Instrumentation is behind one telemetry bootstrap and the
  application remains functional when the SDK is disabled.

### Option B: Export Traces, Metrics, and Logs through OTLP

- **Benefits:** One application protocol and one Alloy receiver for all signals;
  uniform resource attributes and exporter configuration.
- **Costs:** Replaces the proven stdout log path with the still-evolving Python
  OpenTelemetry Logs SDK or duplicates every log through stdout and OTLP. It also
  changes the existing Prometheus pull contract unless a second metric reader is
  retained.
- **Failure modes:** Duplicate logs, exporter backpressure, missing startup/shutdown
  logs, or loss of all remote signals through one receiver path.
- **Operability:** Centralized, but harder to diagnose when the collector is down.
- **Testability:** More exporter combinations and duplicate-delivery cases.
- **Security:** A broader OTLP log payload requires additional filtering.
- **Reversibility:** Moderate because log and metric ingestion contracts change.

### Option C: Add Only FastAPI Tracing and Keep Existing Logs and Metrics

- **Benefits:** Smallest code change and no metric migration.
- **Costs:** Does not prove propagation through queued or child-process work and
  leaves application metrics outside the OpenTelemetry framework.
- **Failure modes:** HTTP traces appear healthy while the expensive run has no span
  or correlated worker logs.
- **Operability:** Incomplete causal view of the primary workload.
- **Testability:** Simple but unable to satisfy the required end-to-end correlation.
- **Security:** Similar to the current application, with fewer new fields.
- **Reversibility:** High, but the option does not meet the requirement.

## Recommendation

Choose Option A.

Create an explicit application telemetry bootstrap instead of relying on the
`opentelemetry-instrument` command. Configure an OpenTelemetry resource with a stable
`service.name` of `serving-configuration-portal`, the portal version, environment,
and an externally supplied instance identity. Initialize and shut down providers in
the application lifecycle, support `OTEL_SDK_DISABLED`, use bounded batch export,
and treat exporter failure as an operational signal rather than a request failure.

Instrument FastAPI with `opentelemetry-instrumentation-fastapi`. Exclude liveness,
readiness, and metric-scrape endpoints from tracing to avoid probe noise. Use the
OpenTelemetry logging instrumentation only to inject active `trace_id`, `span_id`,
sampling state, and service identity into Python `LogRecord` objects. Continue to
format logs as one JSON object per stdout line; do not enable application-side OTLP
log export in this increment.

Use the OpenTelemetry Metrics API for portal counters, gauges, and histograms, with a
Prometheus metric reader preserving `GET /metrics`. Keep existing low-cardinality run
and cache signals and add queue/run duration where it is behaviorally useful. Never
use trace ID, span ID, run ID, model name, or user input as a metric attribute.

Use W3C Trace Context as the sole propagation format. At submission, inject the
active context into a plain string carrier stored with the queued run. Pass that
carrier to the production worker, extract it there, and create a manual
`portal.run.execute` span around AIConfigurator. Reconstruct context explicitly in
completion and timeout callbacks instead of relying on thread-local ambient context.
Do not propagate arbitrary W3C baggage from untrusted callers.

Run the production process pool with an explicit `spawn` multiprocessing context and
initialize a separate telemetry provider/exporter in the child process. Do not rely
on a forked copy of exporter channels or background threads. Cache hits, rejection,
failure, timeout, and shutdown paths receive explicit spans or events and correlated
lifecycle logs. Polling requests remain independent HTTP traces and correlate to the
submitted work through the existing run ID rather than a stale propagated context.

Deploy Alloy as a separately configured collector with bounded memory and batch
processing:

- receive application traces over OTLP and export them to Tempo;
- collect selected Kubernetes pod stdout, parse the JSON log, retain
  `service_name` as a low-cardinality Loki label, attach `trace_id` and `span_id` as
  structured metadata, and write to Loki; and
- discover and scrape the portal `/metrics` endpoint, then forward metrics to the
  configured Prometheus-compatible destination.

Backend URLs, tenant headers, TLS material, and credentials are supplied through
Secrets or deployment-specific environment configuration and are never committed.
For a standalone Prometheus server, prefer normal scraping; a remote-write receiver
may be used by a bounded local verification stack but is not the default production
ingestion assumption.

Provision stable Grafana data-source UIDs `tempo`, `loki`, and `prometheus`. Configure
the Tempo data source `tracesToLogsV2` integration to query Loki by the span's
`service.name` mapped to the `service_name` log label and by the complete trace ID,
with a small time-window allowance for ingestion delay. Configure the Loki data
source with a `trace_id` derived field and an internal link to the `tempo` data
source. The link uses the raw 32-character lowercase hexadecimal trace ID. Correlate
by trace ID rather than span ID so web, callback, and worker logs from the same trace
remain visible together.

Do not promote `trace_id`, `span_id`, or `run_id` to Loki stream labels. They remain
JSON fields and Loki structured metadata, preventing a stream-cardinality explosion
while retaining query and navigation support.

## Consequences

- **Positive:** One submitted run can be followed from HTTP ingress through queued
  execution and the child process in Tempo.
- **Positive:** Application and worker logs contain the active trace and span IDs and
  remain available from stdout independently of Alloy.
- **Positive:** Grafana provides deterministic Tempo-to-Loki and Loki-to-Tempo links
  from provisioned configuration.
- **Positive:** Existing low-cardinality metrics remain scrapeable from `/metrics`
  while their application instruments use the OpenTelemetry API.
- **Positive:** The telemetry backend can change behind Alloy without changing the
  application protocol.
- **Negative:** Explicit `spawn` may increase worker startup latency and memory use;
  the real AIConfigurator container flow must be remeasured.
- **Negative:** The application has two telemetry delivery mechanisms: OTLP for
  traces and scrape/stdout collection for metrics and logs.
- **Negative:** Grafana correlation depends on consistent resource-to-label mapping,
  data-source UIDs, trace-ID formatting, and adequate query time windows.
- **Negative:** Unsampled traces still propagate but cannot be opened in Tempo; log
  records may contain a trace ID whose trace was intentionally not stored.
- **Follow-up:** Evaluate trace-derived RED metrics, service graphs, exemplars, or
  tail sampling only after the base three-signal pipeline and cardinality are
  measured. They are not required by this decision.

## Validation

1. Unit-test telemetry initialization, idempotence, disabled mode, bounded shutdown,
   JSON formatting, and omission of invalid or inactive trace identifiers.
2. Use an in-memory exporter with a thread-based test executor to prove incoming W3C
   context extraction and the expected FastAPI/run span relationships.
3. Run a real spawned worker against a local OTLP receiver. Submit a request with a
   known valid `traceparent` and prove the HTTP, queued lifecycle, and worker spans
   share the same trace ID even when execution starts after the HTTP response ends.
4. Cover successful execution, queued execution, cache hit, rejection, dependency
   failure, timeout, and shutdown without leaking exception details or sensitive
   inputs.
5. Verify `/metrics` preserves required portal metrics, adds the selected standard
   HTTP metrics, and contains no run, trace, model, or user-derived labels.
6. Validate Alloy syntax and Kubernetes manifests, then prove traces arrive in
   Tempo, JSON logs arrive in Loki with structured trace metadata, and metrics are
   queryable from Prometheus.
7. With Playwright MCP, open the known trace in Grafana Tempo, select **Logs for this
   span**, and confirm Loki returns the same run's web and worker lifecycle logs.
   From one returned log, select **View Trace** and confirm Grafana returns to the
   exact same Tempo trace ID.
8. Confirm malformed or absent trace IDs do not create broken derived links and that
   trace, span, and run identifiers are absent from Loki stream and Prometheus
   labels.
9. Stop Alloy or a backend and prove business requests, probes, and local stdout
   logging remain functional with bounded telemetry resource use.
10. Re-run the real AIConfigurator container flow, the existing Playwright MCP
    regression path, all configured project checks, the image build,
    `kubectl apply --dry-run=client`, and `git diff --check`.

## What Would Change This Decision

- Python OpenTelemetry logs become stable and operational evidence shows one OTLP
  path is more reliable than stdout collection without duplicate delivery.
- The service moves to a durable external queue or Kubernetes Jobs, requiring trace
  propagation through a queue protocol rather than a local process carrier.
- Multiple replicas or multiple Alloy instances require shared tail sampling,
  collector clustering, or a different log collection topology.
- The metrics destination does not support the selected scrape or remote-write
  contract.
- Measured `spawn` overhead is unacceptable for the AIConfigurator workload and a
  separately deployed worker becomes the smaller reliable boundary.
- Grafana changes its correlation provisioning contract or Loki structured metadata
  is unavailable in the deployed backend version.

## Links

- Related requirements: `docs/project-brief.md`
- Related architecture: `ARCHITECTURE.md`
- Related decisions: ADR-001 and ADR-002
- OpenTelemetry Python instrumentation:
  <https://opentelemetry.io/docs/languages/python/instrumentation/>
- OpenTelemetry FastAPI instrumentation:
  <https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html>
- OpenTelemetry logging instrumentation:
  <https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html>
- Grafana Alloy OpenTelemetry pipeline:
  <https://grafana.com/docs/alloy/latest/collect/opentelemetry-to-lgtm-stack/>
- Grafana Loki data-source derived fields:
  <https://grafana.com/docs/grafana/latest/datasources/loki/configure/>
