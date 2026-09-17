"""Bounded asynchronous run lifecycle with an isolated production worker."""

import shutil
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import Executor, Future, ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock, Timer
from typing import Literal
from uuid import uuid4

from portal.adapters import AiconfiguratorAdapter, RunRequest, RunResult
from portal.aiconfigurator import run_ai_configurator
from portal.artifacts import zip_directory
from portal.cache import (
    DEFAULT_CACHE_NAMESPACE,
    BoundedResultCache,
    CacheNamespace,
    result_from_cached_bundle,
)

RunStatus = Literal["queued", "running", "completed", "failed"]
Worker = Callable[[RunRequest, str], RunResult]
CacheEvent = Literal["hit", "miss"]


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
        self._executor = executor or ProcessPoolExecutor(max_workers=max_active)
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
        self._remove_orphaned_run_directories()

    def submit(self, request: RunRequest) -> RunSnapshot:
        """Admit a request or raise ``QueueFullError``."""

        with self._lock:
            self._cleanup_expired_locked()
            if self._closing:
                raise RuntimeError("run service is shutting down")
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
                        )
                        self._records[run_id] = record
                        self._completed_total += 1
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
            )
            self._records[run_id] = record
            self._queue.append(run_id)
            self._start_next_locked()
            return self._snapshot_locked(record)

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
            future = self._executor.submit(self._worker, record.request, str(record.output_dir))
            record.future = future

            timer = Timer(self._timeout_seconds, self._timeout, args=(run_id, future))
            timer.daemon = True
            record.timer = timer
            timer.start()

            def complete(completed: Future[RunResult], run_id: str = run_id) -> None:
                self._complete(run_id, completed)

            future.add_done_callback(complete)

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
    """Production process entry point."""

    return run_ai_configurator(request, output_dir)


def _is_run_id(value: str) -> bool:
    return len(value) == 32 and all(character in "0123456789abcdef" for character in value)
