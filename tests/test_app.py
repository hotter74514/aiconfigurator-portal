"""Application and bounded run lifecycle tests."""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from portal.adapters import FakeAiconfiguratorAdapter, RunRequest, RunResult
from portal.app import create_app
from portal.runs import QueueFullError, RunManager


def _fake_worker(request: RunRequest, output_dir: str) -> RunResult:
    return FakeAiconfiguratorAdapter().run(request, Path(output_dir))


def _slow_fake_worker(request: RunRequest, output_dir: str) -> RunResult:
    time.sleep(0.1)
    return _fake_worker(request, output_dir)


@pytest.mark.integration
def test_app_factory_exposes_liveness_and_metadata() -> None:
    client = TestClient(create_app())

    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/").json()["service"] == "serving-configuration-portal"


def test_fake_adapter_returns_stable_rows_and_artifact(tmp_path: Path) -> None:
    request = RunRequest(
        model="Qwen/Qwen3-32B-FP8",
        system="h200_sxm",
        total_gpus=32,
        ttft_ms=1000,
        tpot_ms=10,
    )

    result = FakeAiconfiguratorAdapter().run(request, tmp_path / "run")

    assert result.source_version == "fake"
    assert result.rows[0].metrics["tokens/s"] == 1.0
    assert (tmp_path / "run" / "fake-k8s-deploy.yaml").is_file()


def test_run_manager_limits_active_and_queued_work(tmp_path: Path) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(
        tmp_path,
        worker=_slow_fake_worker,
        executor=executor,
        max_active=1,
        max_queued=1,
    )
    request = RunRequest("model", "h200_sxm", 1, 1000, 10)
    try:
        first = manager.submit(request)
        second = manager.submit(request)
        assert first.status == "running"
        assert second.status == "queued"
        with pytest.raises(QueueFullError):
            manager.submit(request)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            first_state = manager.snapshot(first.run_id)
            second_state = manager.snapshot(second.run_id)
            if first_state is not None and second_state is not None:
                if first_state.status == "completed" and second_state.status == "completed":
                    break
            time.sleep(0.01)
        first_state = manager.snapshot(first.run_id)
        second_state = manager.snapshot(second.run_id)
        assert first_state is not None
        assert second_state is not None
        assert first_state.status == "completed"
        assert second_state.status == "completed"
    finally:
        manager.close()


def test_run_manager_marks_overdue_work_failed(tmp_path: Path) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(
        tmp_path,
        worker=_slow_fake_worker,
        executor=executor,
        timeout_seconds=0.01,
    )
    try:
        snapshot = manager.submit(RunRequest("model", "h200_sxm", 1, 1000, 10))
        deadline = time.monotonic() + 2
        state = manager.snapshot(snapshot.run_id)
        while state is not None and state.status == "running" and time.monotonic() < deadline:
            time.sleep(0.01)
            state = manager.snapshot(snapshot.run_id)
        assert state is not None
        assert state.status == "failed"
        assert state.error == "run exceeded 0.01s timeout"
    finally:
        manager.close()


def test_run_api_returns_202_and_completed_rows(tmp_path: Path) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(tmp_path, worker=_fake_worker, executor=executor)
    try:
        with TestClient(create_app(manager)) as client:
            response = client.post(
                "/api/runs",
                json={
                    "model": "Qwen/Qwen3-32B-FP8",
                    "system": "H200_SXM",
                    "total_gpus": 32,
                    "ttft": 1000,
                    "tpot": 10,
                },
            )
            assert response.status_code == 202
            run_id = response.json()["run_id"]
            assert response.json()["status_url"] == f"/api/runs/{run_id}"

            deadline = time.monotonic() + 2
            state: dict[str, object] = {}
            while time.monotonic() < deadline:
                state = client.get(f"/api/runs/{run_id}").json()
                if state["status"] == "completed":
                    break
                time.sleep(0.01)
            assert state["status"] == "completed"
            results = state["results"]
            assert isinstance(results, list)
            assert isinstance(results[0], dict)
            metrics = results[0]["metrics"]
            assert isinstance(metrics, dict)
            assert metrics["tokens/s"] == 1.0

            invalid = client.post(
                "/api/runs",
                json={"model": "x", "system": "unknown", "total_gpus": 1, "ttft": 1, "tpot": 1},
            )
            assert invalid.status_code == 422
            assert client.get("/api/runs/not-a-run").status_code == 404
    finally:
        manager.close()
