"""Low-cardinality Prometheus metrics and JSON logging helpers."""

import json
import logging
import sys
from collections.abc import Mapping
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest


class PortalMetrics:
    """Metrics owned by one app instance, safe for isolated test clients."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.submitted = Counter(
            "portal_runs_submitted_total", "Accepted run submissions", registry=self.registry
        )
        self.rejected = Counter(
            "portal_runs_rejected_total", "Rejected run submissions", registry=self.registry
        )
        self.active = Gauge("portal_runs_active", "Currently running jobs", registry=self.registry)
        self.queued = Gauge("portal_runs_queued", "Queued jobs", registry=self.registry)
        self.completed = Gauge(
            "portal_runs_completed_total", "Completed jobs", registry=self.registry
        )
        self.failed = Gauge("portal_runs_failed_total", "Failed jobs", registry=self.registry)
        self.last_duration = Gauge(
            "portal_run_last_duration_seconds",
            "Duration of the most recently terminal run",
            registry=self.registry,
        )
        self.cache_hits = Counter(
            "portal_cache_hits_total", "Completed-result cache hits", registry=self.registry
        )
        self.cache_misses = Counter(
            "portal_cache_misses_total", "Completed-result cache misses", registry=self.registry
        )
        self.cache_evictions = Counter(
            "portal_cache_evictions_total",
            "Completed-result cache evictions",
            registry=self.registry,
        )
        self._cache_observed = {"hits": 0, "misses": 0, "evictions": 0}

    def render(self, stats: Mapping[str, int | float | bool]) -> bytes:
        """Update gauges from manager state and render Prometheus text."""

        self.active.set(int(stats["active"]))
        self.queued.set(int(stats["queued"]))
        self.completed.set(int(stats["completed"]))
        self.failed.set(int(stats["failed"]))
        self.last_duration.set(float(stats["last_duration_seconds"]))
        for key, counter in (
            ("hits", self.cache_hits),
            ("misses", self.cache_misses),
            ("evictions", self.cache_evictions),
        ):
            current = int(stats[f"cache_{key}"])
            delta = current - self._cache_observed[key]
            if delta > 0:
                counter.inc(delta)
            self._cache_observed[key] = current
        return generate_latest(self.registry)


class JsonFormatter(logging.Formatter):
    """Serialize safe log fields as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("event", "run_id", "status", "error_category"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging() -> None:
    """Install one stdout JSON handler for the application process."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
