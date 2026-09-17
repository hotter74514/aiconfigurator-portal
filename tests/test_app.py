"""Application and bounded run lifecycle tests."""

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from portal.adapters import FakeAiconfiguratorAdapter, RunRequest, RunResult
from portal.aiconfigurator import _discover_pareto_frontier
from portal.app import create_app
from portal.runs import QueueFullError, RunManager


def _fake_worker(request: RunRequest, output_dir: str) -> RunResult:
    return FakeAiconfiguratorAdapter().run(request, Path(output_dir))


def _slow_fake_worker(request: RunRequest, output_dir: str) -> RunResult:
    time.sleep(0.1)
    return _fake_worker(request, output_dir)


def _unsafe_visualization_worker(request: RunRequest, output_dir: str) -> RunResult:
    result = _fake_worker(request, output_dir)
    asset = result.visualizations[0]
    if request.model == "escape":
        outside = Path(output_dir).parent / "outside.png"
        outside.write_bytes((Path(output_dir) / asset.relative_path).read_bytes())
        asset = replace(asset, relative_path="../outside.png")
    elif request.model == "symlink":
        image = Path(output_dir) / asset.relative_path
        image.unlink()
        image.symlink_to(Path(output_dir).parent / "outside.png")
    elif request.model == "internal-symlink":
        image = Path(output_dir) / asset.relative_path
        target = Path(output_dir) / "target.png"
        target.write_bytes(image.read_bytes())
        image.unlink()
        image.symlink_to(target)
    else:
        asset = replace(asset, media_type="text/plain")
    return replace(result, visualizations=(asset,))


def _wait_for_completion(client: TestClient, run_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 2
    state: dict[str, object] = {}
    while time.monotonic() < deadline:
        state = client.get(f"/api/runs/{run_id}").json()
        if state["status"] in {"completed", "failed"}:
            return state
        time.sleep(0.01)
    return state


@pytest.mark.integration
def test_app_factory_exposes_liveness_and_metadata() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        page = client.get("/")
        assert page.headers["content-type"].startswith("text/html")
        assert "Serving Configuration Portal" in page.text
        assert "Aggregated vs disaggregated" in page.text
        assert "No universal winner is declared" in page.text


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
    assert len(result.visualizations) == 1
    assert result.visualizations[0].relative_path == "pareto_frontier.png"
    assert result.visualizations[0].media_type == "image/png"


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
            comparison = state["comparison"]
            assert isinstance(comparison, dict)
            assert comparison["available"] is True
            assert comparison["modes"]["agg"]["rank"] == 1
            assert comparison["modes"]["disagg"]["rank"] == 1
            comparison_metrics = {metric["name"]: metric for metric in comparison["metrics"]}
            assert comparison_metrics["tokens/s"]["percentage_delta"] == 100.0
            rendered_metrics = client.get("/metrics").text
            assert "portal_runs_submitted_total 1.0" in rendered_metrics
            assert "portal_runs_completed_total 1.0" in rendered_metrics
            assert "portal_run_last_duration_seconds " in rendered_metrics

            invalid = client.post(
                "/api/runs",
                json={"model": "x", "system": "unknown", "total_gpus": 1, "ttft": 1, "tpot": 1},
            )
            assert invalid.status_code == 422
            assert client.get("/api/runs/not-a-run").status_code == 404
    finally:
        manager.close()


def test_run_api_downloads_only_completed_run_artifacts(tmp_path: Path) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(tmp_path, worker=_fake_worker, executor=executor)
    try:
        with TestClient(create_app(manager)) as client:
            response = client.post(
                "/api/runs",
                json={
                    "model": "model",
                    "system": "h200_sxm",
                    "total_gpus": 1,
                    "ttft": 1,
                    "tpot": 1,
                },
            )
            run_id = response.json()["run_id"]
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if client.get(f"/api/runs/{run_id}").json()["status"] == "completed":
                    break
                time.sleep(0.01)
            download = client.get(f"/api/runs/{run_id}/artifacts")
            assert download.status_code == 200
            assert download.headers["content-type"].startswith("application/zip")
            with ZipFile(BytesIO(download.content)) as archive:
                assert archive.namelist() == ["fake-k8s-deploy.yaml", "pareto_frontier.png"]
    finally:
        manager.close()


def test_run_api_exposes_and_serves_run_scoped_pareto_visualization(tmp_path: Path) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(tmp_path, worker=_fake_worker, executor=executor)
    try:
        with TestClient(create_app(manager)) as client:
            response = client.post(
                "/api/runs",
                json={
                    "model": "model",
                    "system": "h200_sxm",
                    "total_gpus": 1,
                    "ttft": 1,
                    "tpot": 1,
                },
            )
            run_id = response.json()["run_id"]
            state = _wait_for_completion(client, run_id)
            assert state["status"] == "completed"
            visualizations = state["visualizations"]
            assert isinstance(visualizations, list)
            asset = visualizations[0]
            assert asset["media_type"] == "image/png"
            assert asset["width"] == 1
            assert asset["height"] == 1
            assert asset["alt_text"]
            assert asset["caption"]
            assert asset["scope_note"]
            assert asset["axis_note"]

            image = client.get(asset["url"])
            assert image.status_code == 200
            assert image.headers["content-type"].startswith("image/png")
            assert image.content.startswith(b"\x89PNG\r\n\x1a\n")
            assert client.get(f"/api/runs/{run_id}/visualizations/{'a' * 32}").status_code == 404
            assert (
                client.get(f"/api/runs/{'b' * 32}/visualizations/{asset['id']}").status_code == 404
            )
    finally:
        manager.close()


def test_visualization_endpoint_rejects_incomplete_missing_and_unsafe_assets(
    tmp_path: Path,
) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(tmp_path, worker=_slow_fake_worker, executor=executor)
    try:
        with TestClient(create_app(manager)) as client:
            response = client.post(
                "/api/runs",
                json={
                    "model": "model",
                    "system": "h200_sxm",
                    "total_gpus": 1,
                    "ttft": 1,
                    "tpot": 1,
                },
            )
            run_id = response.json()["run_id"]
            assert client.get(f"/api/runs/{run_id}/visualizations/{'a' * 32}").status_code == 409
            state = _wait_for_completion(client, run_id)
            asset_id = state["visualizations"][0]["id"]
            (tmp_path / run_id / "pareto_frontier.png").unlink()
            assert client.get(f"/api/runs/{run_id}/visualizations/{asset_id}").status_code == 404
    finally:
        manager.close()

    for model, expected_status in (
        ("escape", 404),
        ("symlink", 404),
        ("internal-symlink", 404),
        ("unsupported", 415),
    ):
        executor = ThreadPoolExecutor(max_workers=1)
        manager = RunManager(
            tmp_path / model, worker=_unsafe_visualization_worker, executor=executor
        )
        try:
            with TestClient(create_app(manager)) as client:
                response = client.post(
                    "/api/runs",
                    json={
                        "model": model,
                        "system": "h200_sxm",
                        "total_gpus": 1,
                        "ttft": 1,
                        "tpot": 1,
                    },
                )
                run_id = response.json()["run_id"]
                state = _wait_for_completion(client, run_id)
                asset_id = state["visualizations"][0]["id"]
                assert (
                    client.get(f"/api/runs/{run_id}/visualizations/{asset_id}").status_code
                    == expected_status
                )
        finally:
            manager.close()


def test_visualization_endpoint_honors_run_expiry(tmp_path: Path) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(
        tmp_path,
        worker=_fake_worker,
        executor=executor,
        retention_seconds=0.1,
    )
    try:
        with TestClient(create_app(manager)) as client:
            response = client.post(
                "/api/runs",
                json={
                    "model": "model",
                    "system": "h200_sxm",
                    "total_gpus": 1,
                    "ttft": 1,
                    "tpot": 1,
                },
            )
            run_id = response.json()["run_id"]
            state = _wait_for_completion(client, run_id)
            asset_id = state["visualizations"][0]["id"]
            time.sleep(0.15)
            assert client.get(f"/api/runs/{run_id}/visualizations/{asset_id}").status_code == 404
    finally:
        manager.close()


def test_pareto_discovery_requires_one_contained_png(tmp_path: Path) -> None:
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6360f8cfc000000301010018dd8db40000000049454e44ae426082"
    )
    (tmp_path / "pareto_frontier.png").write_bytes(png)
    discovered = _discover_pareto_frontier(tmp_path)
    assert len(discovered) == 1
    assert discovered[0].width == 1
    assert discovered[0].height == 1

    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "pareto_frontier.png").write_bytes(png)
    assert _discover_pareto_frontier(tmp_path) == ()


def test_health_readiness_and_metrics_are_exposed(tmp_path: Path) -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(tmp_path, worker=_fake_worker, executor=executor)
    try:
        with TestClient(create_app(manager)) as client:
            assert client.get("/health/live").status_code == 200
            assert client.get("/health/ready").json() == {"status": "ok"}
            metrics = client.get("/metrics")
            assert metrics.status_code == 200
            assert "portal_runs_active 0.0" in metrics.text
            assert "portal_runs_queued 0.0" in metrics.text
            manager.close()
            assert client.get("/health/ready").status_code == 503
    finally:
        manager.close()


def test_run_manager_expires_terminal_runs_and_cleans_orphans(tmp_path: Path) -> None:
    orphan = tmp_path / ("a" * 32)
    orphan.mkdir()
    (orphan / "old.txt").write_text("old", encoding="utf-8")
    executor = ThreadPoolExecutor(max_workers=1)
    manager = RunManager(
        tmp_path,
        worker=_fake_worker,
        executor=executor,
        retention_seconds=0.01,
    )
    assert not orphan.exists()
    try:
        snapshot = manager.submit(RunRequest("model", "h200_sxm", 1, 1000, 10))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            state = manager.snapshot(snapshot.run_id)
            if state is not None and state.status == "completed":
                break
            time.sleep(0.01)
        time.sleep(0.02)
        assert manager.snapshot(snapshot.run_id) is None
        assert not (tmp_path / snapshot.run_id).exists()
    finally:
        manager.close()
