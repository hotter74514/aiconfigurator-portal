"""Bounded process-local cache for immutable completed run bundles."""

import hashlib
import json
import shutil
import stat
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Final
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from portal.adapters import ConfigurationRow, RunRequest, RunResult, VisualizationAsset
from portal.tradeoff import TradeoffPoint, TradeoffSurface

CACHE_SCHEMA_VERSION: Final[str] = "portal-cache-1"


@dataclass(frozen=True, slots=True)
class CacheNamespace:
    """Version inputs that make a normalized result safe to reuse."""

    aiconfigurator: str
    performance_profile: str
    generator_mapping: str
    normalization: str

    def is_complete(self) -> bool:
        """Return whether every namespace component is known and non-empty."""

        return all(
            isinstance(value, str) and bool(value.strip())
            for value in (
                self.aiconfigurator,
                self.performance_profile,
                self.generator_mapping,
                self.normalization,
            )
        )


DEFAULT_CACHE_NAMESPACE: Final[CacheNamespace] = CacheNamespace(
    aiconfigurator="aiconfigurator-0.11.0",
    performance_profile="default-profile-1.3.0rc10",
    generator_mapping="dynamo-default-triton-llm-1.3.0rc14",
    normalization="portal-normalization-1",
)


@dataclass(frozen=True, slots=True)
class CachedResult:
    """Immutable normalized result and artifact bytes held by the cache."""

    rows: tuple[ConfigurationRow, ...]
    source_version: str
    visualizations: tuple[VisualizationAsset, ...]
    tradeoff_surface: TradeoffSurface | None
    artifact_zip: bytes


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    bundle: CachedResult
    created_at: float
    size_bytes: int


def cache_key(request: RunRequest, namespace: CacheNamespace | None) -> str | None:
    """Hash canonical request and known dependency/normalization versions."""

    if namespace is None or not namespace.is_complete():
        return None
    payload = {
        "cache_schema": CACHE_SCHEMA_VERSION,
        "namespace": {
            "aiconfigurator": namespace.aiconfigurator,
            "generator_mapping": namespace.generator_mapping,
            "normalization": namespace.normalization,
            "performance_profile": namespace.performance_profile,
        },
        "request": {
            "isl": request.isl,
            "model": request.model,
            "osl": request.osl,
            "system": request.system,
            "total_gpus": request.total_gpus,
            "tpot_ms": request.tpot_ms,
            "ttft_ms": request.ttft_ms,
        },
    }
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class BoundedResultCache:
    """Deterministic LRU cache bounded by TTL, count, and artifact bytes."""

    def __init__(
        self,
        namespace: CacheNamespace | None,
        *,
        ttl_seconds: float,
        max_entries: int,
        max_bytes: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0 or max_entries < 1 or max_bytes < 1:
            raise ValueError("cache TTL, entry count, and byte limit must be positive")
        self.namespace = namespace
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._clock = clock
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def key(self, request: RunRequest) -> str | None:
        """Return the configured namespace key, or ``None`` when disabled."""

        return cache_key(request, self.namespace)

    def get(self, key: str) -> CachedResult | None:
        """Return a fresh entry and mark it most recently used."""

        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None
        if self._is_expired(entry):
            self._remove(key)
            self._evictions += 1
            self._misses += 1
            return None
        self._entries.move_to_end(key)
        self._hits += 1
        return entry.bundle

    def put(self, key: str, result: RunResult, artifact_zip: bytes) -> None:
        """Store one successful immutable bundle and evict oldest entries."""

        size_bytes = len(artifact_zip)
        if size_bytes > self._max_bytes:
            return
        bundle = CachedResult(
            rows=tuple(
                ConfigurationRow(row.rank, row.serving_mode, dict(row.metrics))
                for row in result.rows
            ),
            source_version=result.source_version,
            visualizations=tuple(result.visualizations),
            tradeoff_surface=result.tradeoff_surface,
            artifact_zip=bytes(artifact_zip),
        )
        if key in self._entries:
            self._remove(key)
        self._entries[key] = _CacheEntry(bundle, self._clock(), size_bytes)
        self._bytes += size_bytes
        self._evict_to_bounds()

    def discard(self, key: str) -> None:
        """Remove one cache entry without counting a capacity eviction."""

        self._remove(key)

    def stats(self) -> dict[str, int]:
        """Return low-cardinality cache counters and current bounds."""

        self._expire_entries()
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "entries": len(self._entries),
            "bytes": self._bytes,
        }

    def _is_expired(self, entry: _CacheEntry) -> bool:
        return self._clock() - entry.created_at >= self._ttl_seconds

    def _expire_entries(self) -> None:
        for key, entry in tuple(self._entries.items()):
            if self._is_expired(entry):
                self._remove(key)
                self._evictions += 1

    def _evict_to_bounds(self) -> None:
        while len(self._entries) > self._max_entries or self._bytes > self._max_bytes:
            self._entries.popitem(last=False)
            self._evictions += 1
            self._bytes = sum(entry.size_bytes for entry in self._entries.values())

    def _remove(self, key: str) -> None:
        entry = self._entries.pop(key, None)
        if entry is not None:
            self._bytes -= entry.size_bytes


def materialize_cached_artifacts(bundle: CachedResult, output_dir: Path) -> None:
    """Safely expand cached artifact ZIP bytes into a fresh run directory."""

    root = output_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)
    seen: set[str] = set()
    try:
        with ZipFile(BytesIO(bundle.artifact_zip)) as archive:
            for info in archive.infolist():
                name = info.filename
                if name in seen:
                    raise ValueError("cached artifact ZIP contains duplicate paths")
                seen.add(name)
                candidate = (root / name).resolve()
                if not candidate.is_relative_to(root):
                    raise ValueError("cached artifact path escaped run directory")
                mode = (info.external_attr >> 16) & 0o170000
                if stat.S_ISLNK(mode):
                    raise ValueError("cached artifact ZIP contains a symlink")
                if info.is_dir():
                    candidate.mkdir(parents=True, exist_ok=True)
                    continue
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_bytes(archive.read(info))
    except (BadZipFile, OSError, ValueError):
        shutil.rmtree(root, ignore_errors=True)
        raise


def result_from_cached_bundle(bundle: CachedResult, output_dir: Path) -> RunResult:
    """Materialize files and return a fresh run-scoped result object."""

    materialize_cached_artifacts(bundle, output_dir)
    return RunResult(
        rows=tuple(
            ConfigurationRow(row.rank, row.serving_mode, dict(row.metrics)) for row in bundle.rows
        ),
        artifact_dir=output_dir,
        source_version=bundle.source_version,
        visualizations=tuple(
            VisualizationAsset(
                asset_id=_new_asset_id(),
                relative_path=asset.relative_path,
                media_type=asset.media_type,
                width=asset.width,
                height=asset.height,
                alt_text=asset.alt_text,
                caption=asset.caption,
                scope_note=asset.scope_note,
                axis_note=asset.axis_note,
            )
            for asset in bundle.visualizations
        ),
        tradeoff_surface=_copy_tradeoff_surface(bundle.tradeoff_surface),
    )


def _new_asset_id() -> str:
    """Create a fresh opaque visualization identifier without exposing cache keys."""

    return uuid4().hex


def _copy_tradeoff_surface(surface: TradeoffSurface | None) -> TradeoffSurface | None:
    """Copy immutable chart data so cached results have no shared mutable internals."""

    if surface is None:
        return None
    points = tuple(
        TradeoffPoint(
            candidate_id=point.candidate_id,
            serving_mode=point.serving_mode,
            rank=point.rank,
            latency_ms=point.latency_ms,
            throughput_tokens_s=point.throughput_tokens_s,
            is_frontier=point.is_frontier,
        )
        for point in surface.points
    )
    by_id = {point.candidate_id: point for point in points}
    return TradeoffSurface(
        points=points,
        frontier=tuple(by_id[point.candidate_id] for point in surface.frontier),
        source_modes=tuple(surface.source_modes),
    )
