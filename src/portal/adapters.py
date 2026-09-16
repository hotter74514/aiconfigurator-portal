"""Stable adapter boundary around version-specific AIConfigurator behavior."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RunRequest:
    """Validated inputs accepted by a portal run."""

    model: str
    system: str
    total_gpus: int
    ttft_ms: float
    tpot_ms: float
    isl: int = 4000
    osl: int = 1000


@dataclass(frozen=True, slots=True)
class ConfigurationRow:
    """Portal-owned, serializable representation of one ranked estimate."""

    rank: int
    serving_mode: str
    metrics: Mapping[str, float | int | str | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunResult:
    """Result data and generated files returned by an adapter."""

    rows: tuple[ConfigurationRow, ...]
    artifact_dir: Path
    source_version: str


class AiconfiguratorAdapter(Protocol):
    """Dependency seam used by the run service and deterministic tests."""

    def run(self, request: RunRequest, output_dir: Path) -> RunResult:
        """Execute one estimate and write generated artifacts to ``output_dir``."""


class FakeAiconfiguratorAdapter:
    """Small deterministic adapter for app and API tests."""

    def __init__(self, *, source_version: str = "fake") -> None:
        self.source_version = source_version

    def run(self, request: RunRequest, output_dir: Path) -> RunResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "fake-k8s-deploy.yaml").write_text(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: fake-result\n",
            encoding="utf-8",
        )
        row = ConfigurationRow(
            rank=1,
            serving_mode="agg",
            metrics={
                "model": request.model,
                "system": request.system,
                "tokens/s": 1.0,
                "tokens/s/gpu": 1.0 / request.total_gpus,
                "ttft": request.ttft_ms,
                "tpot": request.tpot_ms,
                "num_total_gpus": request.total_gpus,
            },
        )
        return RunResult(rows=(row,), artifact_dir=output_dir, source_version=self.source_version)
