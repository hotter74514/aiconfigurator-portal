"""Baseline application and adapter contract tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from portal.adapters import FakeAiconfiguratorAdapter, RunRequest
from portal.app import create_app


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
