"""OpenTelemetry bootstrap, propagation, logging, and metric contract tests."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from portal.adapters import FakeAiconfiguratorAdapter, RunRequest, RunResult
from portal.app import create_app
from portal.observability import (
    JsonFormatter,
    PortalMetrics,
    Telemetry,
    configure_logging,
    inject_trace_context,
)
from portal.runs import RunManager, execute_worker_with_context


def _fake_worker(request: RunRequest, output_dir: str) -> RunResult:
    return FakeAiconfiguratorAdapter().run(request, Path(output_dir))


def test_json_formatter_includes_active_trace_context() -> None:
    telemetry = Telemetry.create()
    configure_logging()
    logger = logging.getLogger("test")
    formatter = JsonFormatter()

    with telemetry.tracer_provider.get_tracer("test").start_as_current_span("test-span"):
        record = logger.makeRecord("test", 20, __file__, 1, "hello", (), None)
        payload = json.loads(formatter.format(record))

    assert len(payload["trace_id"]) == 32
    assert len(payload["span_id"]) == 16
    assert payload["trace_sampled"] is True
    assert payload["service_name"] == "serving-configuration-portal"
    telemetry.shutdown()


def test_json_formatter_omits_context_without_active_span() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord("test", 20, __file__, 1, "hello", (), None)

    payload = json.loads(formatter.format(record))

    assert "trace_id" not in payload
    assert "span_id" not in payload
    assert "trace_sampled" not in payload


def test_portal_metrics_preserve_prometheus_names_without_high_cardinality_labels() -> None:
    telemetry = Telemetry.create()
    metrics = PortalMetrics(telemetry)
    metrics.submitted.inc()
    rendered = metrics.render(
        {
            "active": 0,
            "queued": 0,
            "completed": 0,
            "failed": 0,
            "last_duration_seconds": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_evictions": 0,
        }
    ).decode()

    assert "portal_runs_submitted_total 1.0" in rendered
    assert "portal_cache_evictions_total 0.0" in rendered
    assert "trace_id" not in rendered
    assert "run_id" not in rendered
    telemetry.shutdown()


def test_disabled_sdk_keeps_http_path_available(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    telemetry = Telemetry.create()
    manager = RunManager(tmp_path, executor=ThreadPoolExecutor(1))
    try:
        with TestClient(create_app(manager, telemetry=telemetry)) as client:
            response = client.get("/health/live")
        assert response.status_code == 200
        assert telemetry.enabled is False
        assert telemetry.render_metrics() == b""
    finally:
        manager.close()
        telemetry.shutdown()


def test_fastapi_extracts_incoming_traceparent_and_excludes_probes(tmp_path: Path) -> None:
    exporter = InMemorySpanExporter()
    telemetry = Telemetry.create(span_exporter=exporter)
    manager = RunManager(tmp_path, executor=ThreadPoolExecutor(1))
    trace_id = "0123456789abcdef0123456789abcdef"
    parent_id = "0123456789abcdef"
    traceparent = f"00-{trace_id}-{parent_id}-01"
    try:
        with TestClient(create_app(manager, telemetry=telemetry)) as client:
            assert (
                client.get("/health/live", headers={"traceparent": traceparent}).status_code == 200
            )
            assert (
                client.get("/api/capacity", headers={"traceparent": traceparent}).status_code == 200
            )
            metrics_body = client.get("/metrics").text
        spans = exporter.get_finished_spans()
        assert any(span.name == "GET /api/capacity" for span in spans)
        assert not any(span.name == "GET /health/live" for span in spans)
        capacity_span = next(span for span in spans if span.name == "GET /api/capacity")
        assert f"{capacity_span.context.trace_id:032x}" == trace_id
        assert "http_server_duration_milliseconds" in metrics_body
        assert "trace_id" not in metrics_body
        assert "run_id" not in metrics_body
    finally:
        manager.close()


def test_worker_preserves_trace_context_after_http_submission(tmp_path: Path) -> None:
    exporter = InMemorySpanExporter()
    telemetry = Telemetry.create(span_exporter=exporter)
    request = RunRequest(
        model="Qwen/Qwen3-32B",
        system="H200",
        total_gpus=8,
        ttft_ms=100,
        tpot_ms=20,
    )
    try:
        with telemetry.tracer.start_as_current_span("portal.run.submit") as submit_span:
            carrier = inject_trace_context()
            execute_worker_with_context(
                _fake_worker,
                request,
                str(tmp_path / "run"),
                carrier,
                run_id="run-1",
                telemetry=telemetry,
            )
            submit_context = submit_span.get_span_context()
        telemetry.force_flush()
        spans = exporter.get_finished_spans()
        execute_span = next(span for span in spans if span.name == "portal.run.execute")
        assert execute_span.context.trace_id == submit_context.trace_id
        assert execute_span.parent is not None
        assert execute_span.parent.span_id == submit_context.span_id
    finally:
        telemetry.shutdown()


def test_callback_lifecycle_span_reconstructs_submission_context(tmp_path: Path) -> None:
    exporter = InMemorySpanExporter()
    telemetry = Telemetry.create(span_exporter=exporter)
    manager = RunManager(
        tmp_path,
        worker=_fake_worker,
        executor=ThreadPoolExecutor(1),
        tracer=telemetry.tracer,
    )
    request = RunRequest(
        model="Qwen/Qwen3-32B",
        system="H200",
        total_gpus=8,
        ttft_ms=100,
        tpot_ms=20,
    )
    try:
        with telemetry.tracer.start_as_current_span("portal.http.request") as request_span:
            carrier = inject_trace_context()
            snapshot = manager.submit(request, trace_carrier=carrier)
            request_context = request_span.get_span_context()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            completed = manager.snapshot(snapshot.run_id)
            if completed is not None and completed.status == "completed":
                break
            time.sleep(0.01)
        telemetry.force_flush()
        completed_span = next(
            span for span in exporter.get_finished_spans() if span.name == "portal.run_completed"
        )
        assert completed_span.context.trace_id == request_context.trace_id
        assert completed_span.parent is not None
        assert completed_span.parent.span_id == request_context.span_id
    finally:
        manager.close()
        telemetry.shutdown()


def test_spawned_worker_completes_with_w3c_carrier(tmp_path: Path) -> None:
    telemetry = Telemetry.create()
    manager = RunManager(tmp_path, worker=_fake_worker, max_active=1, max_queued=0)
    request = RunRequest(
        model="Qwen/Qwen3-32B",
        system="H200",
        total_gpus=8,
        ttft_ms=100,
        tpot_ms=20,
    )
    try:
        with telemetry.tracer.start_as_current_span("portal.http.request"):
            snapshot = manager.submit(request, trace_carrier=inject_trace_context())
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            completed = manager.snapshot(snapshot.run_id)
            if completed is not None and completed.status in {"completed", "failed"}:
                break
            time.sleep(0.02)
        assert completed is not None
        assert completed.status == "completed"
    finally:
        manager.close()
        telemetry.shutdown()
