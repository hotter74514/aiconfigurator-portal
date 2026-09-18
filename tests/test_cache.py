"""Bounded completed-result cache tests."""

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Lock

from portal.adapters import FakeAiconfiguratorAdapter, RunRequest, RunResult
from portal.artifacts import zip_directory
from portal.cache import BoundedResultCache, CacheNamespace, cache_key
from portal.runs import RunManager

NAMESPACE = CacheNamespace(
    aiconfigurator="aiconfigurator-0.11.0",
    performance_profile="profile-1.3.0rc10",
    generator_mapping="generator-1.3.0rc14",
    normalization="portal-normalization-1",
)


def _request(*, isl: int = 3000) -> RunRequest:
    return RunRequest("model", "h200_sxm", 1, 1000, 10, isl=isl, osl=512)


def _result(tmp_path: Path, value: float = 1.0) -> RunResult:
    return FakeAiconfiguratorAdapter().run(_request(), tmp_path / f"result-{value}")


def _wait_for_terminal(manager: RunManager, run_id: str) -> object:
    deadline = time.monotonic() + 2
    state = manager.snapshot(run_id)
    while state is not None and state.status not in {"completed", "failed"}:
        if time.monotonic() >= deadline:
            break
        time.sleep(0.01)
        state = manager.snapshot(run_id)
    assert state is not None
    return state


class CountingWorker:
    def __init__(self, *, delay: float = 0.0, fail: bool = False) -> None:
        self.calls = 0
        self._delay = delay
        self._fail = fail
        self._lock = Lock()

    def __call__(self, request: RunRequest, output_dir: str) -> RunResult:
        with self._lock:
            self.calls += 1
        if self._delay:
            time.sleep(self._delay)
        if self._fail:
            raise RuntimeError("dependency unavailable")
        return FakeAiconfiguratorAdapter().run(request, Path(output_dir))


def test_cache_key_is_canonical_and_versioned() -> None:
    request = _request()
    assert cache_key(request, NAMESPACE) == cache_key(request, replace(NAMESPACE))
    for field in (
        "aiconfigurator",
        "performance_profile",
        "generator_mapping",
        "normalization",
    ):
        changed = replace(NAMESPACE, **{field: f"{field}-next"})
        assert cache_key(request, changed) != cache_key(request, NAMESPACE)
    assert cache_key(replace(request, isl=4000), NAMESPACE) != cache_key(request, NAMESPACE)
    assert cache_key(request, None) is None


def test_cache_has_ttl_count_and_byte_bounded_lru(tmp_path: Path) -> None:
    now = [0.0]
    cache = BoundedResultCache(
        NAMESPACE, ttl_seconds=10, max_entries=2, max_bytes=10, clock=lambda: now[0]
    )
    first = cache_key(_request(isl=1), NAMESPACE)
    second = cache_key(_request(isl=2), NAMESPACE)
    third = cache_key(_request(isl=3), NAMESPACE)
    assert first is not None and second is not None and third is not None

    cache.put(first, _result(tmp_path, 1), b"one")
    cache.put(second, _result(tmp_path, 2), b"two")
    assert cache.get(first) is not None
    cache.put(third, _result(tmp_path, 3), b"tri")
    assert cache.get(second) is None
    assert cache.get(first) is not None

    now[0] = 11
    assert cache.get(first) is None
    stats = cache.stats()
    assert stats == {"hits": 2, "misses": 2, "evictions": 3, "entries": 0, "bytes": 0}

    byte_cache = BoundedResultCache(
        NAMESPACE, ttl_seconds=10, max_entries=5, max_bytes=4, clock=lambda: now[0]
    )
    byte_first = cache_key(_request(isl=4), NAMESPACE)
    byte_second = cache_key(_request(isl=5), NAMESPACE)
    assert byte_first is not None and byte_second is not None
    byte_cache.put(byte_first, _result(tmp_path, 4), b"1234")
    byte_cache.put(byte_second, _result(tmp_path, 5), b"5678")
    assert byte_cache.get(byte_first) is None
    assert byte_cache.get(byte_second) is not None
    assert byte_cache.stats()["evictions"] == 1


def test_cache_hit_uses_one_worker_and_fresh_run_with_equivalent_artifacts(
    tmp_path: Path,
) -> None:
    worker = CountingWorker()
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(tmp_path, worker=worker, executor=executor, cache_namespace=NAMESPACE)
    try:
        first = manager.submit(_request())
        first_state = _wait_for_terminal(manager, first.run_id)
        assert first.cache_event == "miss"
        assert first_state.status == "completed"
        assert first_state.result is not None
        first_zip = zip_directory(first_state.result.artifact_dir)

        second = manager.submit(_request())
        assert second.cache_event == "hit"
        assert second.status == "completed"
        second_state = manager.snapshot(second.run_id)
        assert second_state is not None
        assert second_state.result is not None
        assert second.run_id != first.run_id
        assert second_state.result.rows == first_state.result.rows
        assert second_state.result.tradeoff_surface == first_state.result.tradeoff_surface
        assert zip_directory(second_state.result.artifact_dir) == first_zip
        assert worker.calls == 1
    finally:
        manager.close()


def test_cache_does_not_coalesce_in_flight_work_or_cache_failures(tmp_path: Path) -> None:
    worker = CountingWorker(delay=0.05)
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(
        tmp_path / "in-flight", worker=worker, executor=executor, cache_namespace=NAMESPACE
    )
    try:
        first = manager.submit(_request())
        second = manager.submit(_request())
        assert first.cache_event == "miss"
        assert second.cache_event == "miss"
        assert _wait_for_terminal(manager, first.run_id).status == "completed"
        assert _wait_for_terminal(manager, second.run_id).status == "completed"
        assert worker.calls == 2
    finally:
        manager.close()

    failing_worker = CountingWorker(fail=True)
    executor = ThreadPoolExecutor(max_workers=1)
    failed_manager = RunManager(
        tmp_path / "failure", worker=failing_worker, executor=executor, cache_namespace=NAMESPACE
    )
    try:
        first = failed_manager.submit(_request())
        assert _wait_for_terminal(failed_manager, first.run_id).status == "failed"
        second = failed_manager.submit(_request())
        assert second.cache_event == "miss"
        assert _wait_for_terminal(failed_manager, second.run_id).status == "failed"
        assert failing_worker.calls == 2
    finally:
        failed_manager.close()


def test_run_expiry_does_not_expire_cache_entry(tmp_path: Path) -> None:
    worker = CountingWorker()
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(
        tmp_path,
        worker=worker,
        executor=executor,
        cache_namespace=NAMESPACE,
        retention_seconds=0.02,
        cache_ttl_seconds=10,
    )
    try:
        first = manager.submit(_request())
        assert _wait_for_terminal(manager, first.run_id).status == "completed"
        time.sleep(0.03)
        assert manager.snapshot(first.run_id) is None
        second = manager.submit(_request())
        assert second.cache_event == "hit"
        assert worker.calls == 1
    finally:
        manager.close()


def test_cache_is_lost_when_run_manager_is_recreated(tmp_path: Path) -> None:
    first_worker = CountingWorker()
    executor = ThreadPoolExecutor(max_workers=1)
    first_manager = RunManager(
        tmp_path, worker=first_worker, executor=executor, cache_namespace=NAMESPACE
    )
    try:
        first = first_manager.submit(_request())
        assert _wait_for_terminal(first_manager, first.run_id).status == "completed"
    finally:
        first_manager.close()

    second_worker = CountingWorker()
    executor = ThreadPoolExecutor(max_workers=1)
    second_manager = RunManager(
        tmp_path, worker=second_worker, executor=executor, cache_namespace=NAMESPACE
    )
    try:
        second = second_manager.submit(_request())
        assert second.cache_event == "miss"
        assert _wait_for_terminal(second_manager, second.run_id).status == "completed"
        assert second_worker.calls == 1
    finally:
        second_manager.close()
