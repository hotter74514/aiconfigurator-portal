"""OpenTelemetry bootstrap, low-cardinality metrics, and JSON logging."""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock
from typing import Any

from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace import Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import CollectorRegistry, generate_latest

_LOGGING_INSTRUMENTOR = LoggingInstrumentor()
_LOGGING_LOCK = Lock()
TraceCarrier = dict[str, str]


def _env_flag(name: str) -> bool:
    """Return whether a standard boolean environment setting is enabled."""

    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _otlp_traces_configured() -> bool:
    """Avoid opening a default localhost exporter unless explicitly configured."""

    exporters = os.getenv("OTEL_TRACES_EXPORTER", "").strip().lower()
    if exporters == "none":
        return False
    return bool(
        os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or "otlp" in exporters.split(",")
    )


def inject_trace_context() -> TraceCarrier:
    """Serialize only W3C Trace Context from the current active span."""

    carrier: TraceCarrier = {}
    TraceContextTextMapPropagator().inject(carrier)
    return carrier


def extract_trace_context(carrier: Mapping[str, str]) -> Context:
    """Extract W3C Trace Context without accepting arbitrary baggage."""

    return TraceContextTextMapPropagator().extract(carrier=carrier)


@dataclass(slots=True)
class Telemetry:
    """Own one app instance's providers and its Prometheus registry."""

    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    registry: CollectorRegistry
    enabled: bool
    _shutdown: bool = False

    @classmethod
    def create(
        cls,
        *,
        service_name: str = "serving-configuration-portal",
        service_version: str = "0.1.0",
        span_exporter: SpanExporter | None = None,
    ) -> Telemetry:
        """Create providers with explicit, bounded exporter behavior."""

        disabled = _env_flag("OTEL_SDK_DISABLED")
        registry = CollectorRegistry()
        resource = Resource.create(
            {
                "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
                "service.version": service_version,
                "deployment.environment.name": os.getenv(
                    "OTEL_DEPLOYMENT_ENVIRONMENT", "development"
                ),
            }
        )
        if disabled:
            tracer_provider = TracerProvider(resource=resource, shutdown_on_exit=False)
            meter_provider = MeterProvider(resource=resource, shutdown_on_exit=False)
            return cls(tracer_provider, meter_provider, registry, enabled=False)

        if span_exporter is None and _otlp_traces_configured():
            span_exporter = OTLPSpanExporter()
        tracer_provider = TracerProvider(resource=resource, shutdown_on_exit=False)
        if span_exporter is not None:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    span_exporter,
                    max_queue_size=int(os.getenv("OTEL_BSP_MAX_QUEUE_SIZE", "2048")),
                    max_export_batch_size=int(os.getenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512")),
                    schedule_delay_millis=float(os.getenv("OTEL_BSP_SCHEDULE_DELAY", "5000")),
                )
            )
        reader = PrometheusMetricReader(
            disable_target_info=True,
            scope_info_enabled=False,
            registry=registry,
        )
        meter_provider = MeterProvider(
            metric_readers=[reader],
            resource=resource,
            shutdown_on_exit=False,
        )
        return cls(tracer_provider, meter_provider, registry, enabled=True)

    def shutdown(self) -> None:
        """Flush and close providers during app shutdown."""

        if self._shutdown:
            return
        self._shutdown = True
        try:
            self.tracer_provider.shutdown()
        finally:
            self.meter_provider.shutdown()

    def force_flush(self, timeout_millis: int = 5_000) -> bool:
        """Flush pending spans without making exporter failure business-fatal."""

        try:
            return self.tracer_provider.force_flush(timeout_millis)
        except Exception:  # noqa: BLE001 - telemetry must not break application work
            return False

    @property
    def tracer(self) -> Tracer:
        """Return the application tracer used for manual lifecycle spans."""

        return self.tracer_provider.get_tracer("portal.lifecycle")

    def render_metrics(self) -> bytes:
        """Render this app instance's Prometheus registry."""

        return generate_latest(self.registry)


class _Counter:
    """Keep the existing ``inc`` call shape over an OTel counter."""

    def __init__(self, instrument: Any) -> None:
        self._instrument = instrument
        self._instrument.add(0)

    def inc(self, amount: int | float = 1) -> None:
        self._instrument.add(amount)


class _Gauge:
    """Expose a settable gauge using an OTel up-down counter."""

    def __init__(self, instrument: Any) -> None:
        self._instrument = instrument
        self._value = 0.0
        self._instrument.add(0)

    def set(self, value: int | float) -> None:
        numeric = float(value)
        self._instrument.add(numeric - self._value)
        self._value = numeric


class PortalMetrics:
    """Low-cardinality portal metrics backed by the OpenTelemetry API."""

    def __init__(self, telemetry: Telemetry | None = None) -> None:
        self.telemetry = telemetry or Telemetry.create()
        meter = self.telemetry.meter_provider.get_meter("portal.observability")
        self.submitted = _Counter(meter.create_counter("portal_runs_submitted"))
        self.rejected = _Counter(meter.create_counter("portal_runs_rejected"))
        self.active = _Gauge(meter.create_up_down_counter("portal_runs_active"))
        self.queued = _Gauge(meter.create_up_down_counter("portal_runs_queued"))
        self.completed = _Counter(meter.create_counter("portal_runs_completed"))
        self.failed = _Counter(meter.create_counter("portal_runs_failed"))
        self.last_duration = _Gauge(
            meter.create_up_down_counter("portal_run_last_duration_seconds")
        )
        self.duration = meter.create_histogram("portal_run_duration_seconds", unit="s")
        self.cache_hits = _Counter(meter.create_counter("portal_cache_hits"))
        self.cache_misses = _Counter(meter.create_counter("portal_cache_misses"))
        self.cache_evictions = _Counter(meter.create_counter("portal_cache_evictions"))
        self._observed = {
            "completed": 0,
            "failed": 0,
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        self._observed_duration = 0.0

    @property
    def registry(self) -> CollectorRegistry:
        """Expose the app-local registry for compatibility with callers/tests."""

        return self.telemetry.registry

    def render(self, stats: Mapping[str, int | float | bool]) -> bytes:
        """Update state metrics from manager stats and render Prometheus text."""

        self.active.set(int(stats["active"]))
        self.queued.set(int(stats["queued"]))
        self.last_duration.set(float(stats["last_duration_seconds"]))
        duration = float(stats["last_duration_seconds"])
        if duration != self._observed_duration and duration > 0:
            self.duration.record(duration)
            self._observed_duration = duration
        for key, counter in (
            ("completed", self.completed),
            ("failed", self.failed),
            ("hits", self.cache_hits),
            ("misses", self.cache_misses),
            ("evictions", self.cache_evictions),
        ):
            current = int(stats.get(f"cache_{key}", stats.get(key, 0)))
            delta = current - self._observed[key]
            if delta > 0:
                counter.inc(delta)
            self._observed[key] = current
        return self.telemetry.render_metrics()


class JsonFormatter(logging.Formatter):
    """Serialize safe log fields and active OpenTelemetry context as JSON."""

    def __init__(self, service_name: str = "serving-configuration-portal") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service_name": self.service_name,
        }
        trace_id = getattr(record, "otelTraceID", "")
        span_id = getattr(record, "otelSpanID", "")
        if trace_id and set(trace_id) != {"0"}:
            payload["trace_id"] = trace_id
        if span_id and set(span_id) != {"0"}:
            payload["span_id"] = span_id
        if trace_id and set(trace_id) != {"0"} and hasattr(record, "otelTraceSampled"):
            payload["trace_sampled"] = record.otelTraceSampled
        for key in ("event", "run_id", "status", "error_category"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging(service_name: str = "serving-configuration-portal") -> None:
    """Install trace-context injection and one stdout JSON handler."""

    with _LOGGING_LOCK:
        if not getattr(_LOGGING_INSTRUMENTOR, "_is_instrumented_by_opentelemetry", False):
            _LOGGING_INSTRUMENTOR.instrument(inject_trace_context=True)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
