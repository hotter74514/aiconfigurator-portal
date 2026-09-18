"""Bounded asynchronous run lifecycle with an isolated production worker."""

import logging
import multiprocessing
import shutil
import time
from collections import deque
from collections.abc import Callable, Iterator
from concurrent.futures import Executor, Future, ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock, Timer
from typing import Literal
from uuid import uuid4

from opentelemetry.trace import Span, Status, StatusCode, Tracer

from portal.adapters import AiconfiguratorAdapter, RunRequest, RunResult
from portal.aiconfigurator import run_ai_configurator
from portal.artifacts import zip_directory
from portal.cache import (
    DEFAULT_CACHE_NAMESPACE,
    BoundedResultCache,
    CacheNamespace,
    result_from_cached_bundle,
)
from portal.observability import Telemetry, TraceCarrier, configure_logging, extract_trace_context

RunStatus = Literal["queued", "running", "completed", "failed"]
Worker = Callable[[RunRequest, str], RunResult]
CacheEvent = Literal["hit", "miss"]
_logger = logging.getLogger("portal.runs")


class QueueFullError(Exception):
    """Raised when active and queued capacity is exhausted."""


@dataclass
class _RunRecord:
    run_id: str
    request: RunRequest
    output_dir: Path
    status: RunStatus = "queued"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    result: RunResult | None = None
    error: str | None = None
    cache_event: CacheEvent | None = None
    trace_carrier: TraceCarrier = field(default_factory=dict, repr=False)
    future: Future[RunResult] | None = field(default=None, repr=False)
    timer: Timer | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    """Immutable view of run state for an HTTP response."""

    run_id: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    result: RunResult | None
    error: str | None
    cache_event: CacheEvent | None = None


class RunManager:
    """Admit bounded work and execute one run at a time."""

    def __init__(
        self,
        root_dir: Path,
        *,
        adapter: AiconfiguratorAdapter | None = None,
        worker: Worker | None = None,
        executor: Executor | None = None,
        max_active: int = 1,
        max_queued: int = 4,
        timeout_seconds: float = 900.0,
        retention_seconds: float = 3600.0,
        cache_namespace: CacheNamespace | None = DEFAULT_CACHE_NAMESPACE,
        cache_ttl_seconds: float = 3600.0,
        cache_max_entries: int = 32,
        cache_max_bytes: int = 64 * 1024 * 1024,
        cache_clock: Callable[[], float] = time.monotonic,
        tracer: Tracer | None = None,
    ) -> None:
        if max_active < 1 or max_queued < 0 or timeout_seconds <= 0 or retention_seconds <= 0:
            raise ValueError("run capacity, timeout, and retention must be positive")
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._worker = worker or _adapter_worker
        if adapter is not None and worker is not None:
            raise ValueError("provide adapter or worker, not both")
        if adapter is not None:
            self._worker = _make_adapter_worker(adapter)
        self._executor = executor or ProcessPoolExecutor(
            max_workers=max_active,
            mp_context=multiprocessing.get_context("spawn"),
        )
        self._max_active = max_active
        self._max_queued = max_queued
        self._timeout_seconds = timeout_seconds
        self._retention_seconds = retention_seconds
        self._cache = BoundedResultCache(
            cache_namespace,
            ttl_seconds=cache_ttl_seconds,
            max_entries=cache_max_entries,
            max_bytes=cache_max_bytes,
            clock=cache_clock,
        )
        self._active = 0
        self._completed_total = 0
        self._failed_total = 0
        self._last_duration_seconds = 0.0
        self._queue: deque[str] = deque()
        self._records: dict[str, _RunRecord] = {}
        self._lock = RLock()
        self._closing = False
        self._tracer = tracer
        self._remove_orphaned_run_directories()

    def submit(
        self,
        request: RunRequest,
        *,
        trace_carrier: TraceCarrier | None = None,
    ) -> RunSnapshot:
        """Admit a request or raise ``QueueFullError``."""

        with self._lock:
            self._cleanup_expired_locked()
            if self._closing:
                raise RuntimeError("run service is shutting down")
            carrier = dict(trace_carrier or {})
            cache_key = self._cache.key(request)
            cache_event: CacheEvent | None = None
            if cache_key is not None:
                cached = self._cache.get(cache_key)
                if cached is not None:
                    run_id = uuid4().hex
                    output_dir = self.root_dir / run_id
                    try:
                        result = result_from_cached_bundle(cached, output_dir)
                    except (OSError, ValueError):
                        self._cache.discard(cache_key)
                    else:
                        record = _RunRecord(
                            run_id=run_id,
                            request=request,
                            output_dir=output_dir,
                            status="completed",
                            result=result,
                            cache_event="hit",
                            trace_carrier=carrier,
                        )
                        self._records[run_id] = record
                        self._completed_total += 1
                        self._emit_event(
                            record,
                            event="run_cache_hit",
                            status="completed",
                        )
                        return self._snapshot_locked(record)
                cache_event = "miss"
            if self._active + len(self._queue) >= self._max_active + self._max_queued:
                raise QueueFullError
            run_id = uuid4().hex
            record = _RunRecord(
                run_id=run_id,
                request=request,
                output_dir=self.root_dir / run_id,
                cache_event=cache_event,
                trace_carrier=carrier,
            )
            self._records[run_id] = record
            self._queue.append(run_id)
            self._start_next_locked()
            return self._snapshot_locked(record)

    def set_tracer(self, tracer: Tracer | None) -> None:
        """Attach the app-owned tracer to lifecycle callbacks."""

        with self._lock:
            self._tracer = tracer

    def snapshot(self, run_id: str) -> RunSnapshot | None:
        """Return a stable view or ``None`` for an unknown run."""

        with self._lock:
            self._cleanup_expired_locked()
            record = self._records.get(run_id)
            return None if record is None else self._snapshot_locked(record)

    def stats(self) -> dict[str, int | float | bool]:
        """Return low-cardinality service state for metrics and readiness."""

        with self._lock:
            return {
                "active": self._active,
                "queued": len(self._queue),
                "completed": self._completed_total,
                "failed": self._failed_total,
                "last_duration_seconds": self._last_duration_seconds,
                "ready": not self._closing,
                **{
                    f"cache_{key}": value
                    for key, value in self._cache.stats().items()
                    if key in {"hits", "misses", "evictions"}
                },
            }

    def capacity(self) -> dict[str, int | bool]:
        """Return anonymous aggregate admission pressure without run details."""

        with self._lock:
            active = self._active
            queued = len(self._queue)
            return {
                "active": active,
                "queued": queued,
                "active_capacity": self._max_active,
                "queue_capacity": self._max_queued,
                "admission_open": not self._closing
                and active + queued < self._max_active + self._max_queued,
            }

    def close(self) -> None:
        """Stop admission and cancel queued work during application shutdown."""

        with self._lock:
            if self._closing:
                return
            self._closing = True
            while self._queue:
                run_id = self._queue.popleft()
                record = self._records[run_id]
                record.status = "failed"
                record.error = "service shutting down"
                record.updated_at = datetime.now(UTC)
                self._failed_total += 1
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _remove_orphaned_run_directories(self) -> None:
        """Remove only UUID-named directories left by a previous process."""

        for child in self.root_dir.iterdir():
            if child.is_dir() and _is_run_id(child.name):
                shutil.rmtree(child)

    def _cleanup_expired_locked(self) -> None:
        now = datetime.now(UTC)
        expired = [
            run_id
            for run_id, record in self._records.items()
            if record.status in {"completed", "failed"}
            and (now - record.updated_at).total_seconds() >= self._retention_seconds
        ]
        for run_id in expired:
            record = self._records.pop(run_id)
            if record.output_dir.exists():
                shutil.rmtree(record.output_dir)

    def _start_next_locked(self) -> None:
        while self._active < self._max_active and self._queue and not self._closing:
            run_id = self._queue.popleft()
            record = self._records[run_id]
            record.status = "running"
            record.updated_at = datetime.now(UTC)
            self._active += 1
            future = self._executor.submit(
                _worker_entry,
                self._worker,
                record.request,
                str(record.output_dir),
                record.trace_carrier,
                record.run_id,
            )
            record.future = future

            timer = Timer(self._timeout_seconds, self._timeout, args=(run_id, future))
            timer.daemon = True
            record.timer = timer
            timer.start()

            def complete(completed: Future[RunResult], run_id: str = run_id) -> None:
                self._complete(run_id, completed)

            future.add_done_callback(complete)

    @contextmanager
    def _lifecycle_span(self, name: str, record: _RunRecord) -> Iterator[Span | None]:
        """Start a lifecycle span from the submission context when configured."""

        if self._tracer is None or not record.trace_carrier:
            yield None
            return
        context = extract_trace_context(record.trace_carrier)
        with self._tracer.start_as_current_span(name, context=context) as span:
            span.set_attribute("portal.run.id", record.run_id)
            yield span

    def _emit_event(
        self,
        record: _RunRecord,
        *,
        event: str,
        status: RunStatus,
        error_category: str | None = None,
    ) -> None:
        """Emit one safe lifecycle log and optional span."""

        with self._lifecycle_span(f"portal.{event}", record) as span:
            if span is not None:
                span.set_attribute("portal.run.status", status)
                if error_category is not None:
                    span.set_attribute("error.type", error_category)
                    span.set_status(Status(StatusCode.ERROR, error_category))
            extra: dict[str, str] = {
                "event": event,
                "run_id": record.run_id,
                "status": status,
            }
            if error_category is not None:
                extra["error_category"] = error_category
            _logger.info(event.replace("_", " "), extra=extra)

    def _complete(self, run_id: str, future: Future[RunResult]) -> None:
        error: str | None
        artifact_zip: bytes | None = None
        try:
            result = future.result()
        except Exception as exc:  # noqa: BLE001 - normalize dependency failures at the boundary
            status: RunStatus = "failed"
            error = f"{type(exc).__name__}: {str(exc)[:300]}"
            result = None
        else:
            status = "completed"
            error = None
            assert result is not None
            try:
                artifact_zip = zip_directory(result.artifact_dir)
            except (FileNotFoundError, OSError, ValueError):
                artifact_zip = None
        with self._lock:
            record = self._records[run_id]
            if record.status != "running" or record.future is not future:
                return
            if record.timer is not None:
                record.timer.cancel()
            record.status = status
            record.result = result
            record.error = error
            record.updated_at = datetime.now(UTC)
            self._last_duration_seconds = (record.updated_at - record.created_at).total_seconds()
            self._active -= 1
            if status == "completed":
                self._completed_total += 1
                if result is not None and artifact_zip is not None:
                    cache_key = self._cache.key(record.request)
                    if cache_key is not None:
                        self._cache.put(cache_key, result, artifact_zip)
            else:
                self._failed_total += 1
            self._emit_event(
                record,
                event="run_completed" if status == "completed" else "run_failed",
                status=status,
                error_category=_error_category(error),
            )
            self._start_next_locked()

    def _timeout(self, run_id: str, future: Future[RunResult]) -> None:
        """Fail an overdue run and allow the bounded queue to advance."""

        with self._lock:
            record = self._records[run_id]
            if record.status != "running" or record.future is not future:
                return
            future.cancel()
            record.status = "failed"
            record.error = f"run exceeded {self._timeout_seconds:g}s timeout"
            record.updated_at = datetime.now(UTC)
            self._last_duration_seconds = (record.updated_at - record.created_at).total_seconds()
            self._active -= 1
            self._failed_total += 1
            self._emit_event(
                record,
                event="run_timed_out",
                status="failed",
                error_category="timeout",
            )
            self._start_next_locked()

    @staticmethod
    def _snapshot_locked(record: _RunRecord) -> RunSnapshot:
        return RunSnapshot(
            run_id=record.run_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            result=record.result,
            error=record.error,
            cache_event=record.cache_event,
        )


def _make_adapter_worker(adapter: AiconfiguratorAdapter) -> Worker:
    """Build a worker closure for test executors."""

    def run(request: RunRequest, output_dir: str) -> RunResult:
        return adapter.run(request, Path(output_dir))

    return run


def _adapter_worker(request: RunRequest, output_dir: str) -> RunResult:
    """Production adapter entry point."""

    return run_ai_configurator(request, output_dir)


def _worker_entry(
    worker: Worker,
    request: RunRequest,
    output_dir: str,
    trace_carrier: TraceCarrier,
    run_id: str,
) -> RunResult:
    """Execute one worker with a child-owned provider and extracted context."""

    if not trace_carrier:
        return worker(request, output_dir)
    configure_logging()
    telemetry = Telemetry.create()
    try:
        return execute_worker_with_context(
            worker,
            request,
            output_dir,
            trace_carrier,
            run_id=run_id,
            telemetry=telemetry,
        )
    finally:
        telemetry.shutdown()


def execute_worker_with_context(
    worker: Worker,
    request: RunRequest,
    output_dir: str,
    trace_carrier: TraceCarrier,
    *,
    run_id: str = "unknown",
    telemetry: Telemetry | None = None,
) -> RunResult:
    """Execute a worker under the W3C context; exposed for deterministic tests."""

    owned_telemetry = telemetry is None
    active_telemetry = telemetry or Telemetry.create()
    context = extract_trace_context(trace_carrier)
    try:
        with active_telemetry.tracer.start_as_current_span(
            "portal.run.execute", context=context
        ) as span:
            span.set_attribute("portal.run.id", run_id)
            _logger.info(
                "run started",
                extra={"event": "run_started", "run_id": run_id, "status": "running"},
            )
            try:
                result = worker(request, output_dir)
            except Exception as exc:  # noqa: BLE001 - normalize at the process boundary
                category = type(exc).__name__
                span.set_attribute("error.type", category)
                span.set_status(Status(StatusCode.ERROR, category))
                _logger.error(
                    "run worker failed",
                    extra={
                        "event": "run_worker_failed",
                        "run_id": run_id,
                        "status": "failed",
                        "error_category": category,
                    },
                )
                raise
            span.set_status(Status(StatusCode.OK))
            return result
    finally:
        if owned_telemetry:
            active_telemetry.shutdown()


def _is_run_id(value: str) -> bool:
    return len(value) == 32 and all(character in "0123456789abcdef" for character in value)


def _error_category(error: str | None) -> str | None:
    """Extract the safe exception category from the normalized error string."""

    if not error:
        return None
    return error.split(":", 1)[0]
