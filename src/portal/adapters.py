"""Stable adapter boundary around version-specific AIConfigurator behavior."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from uuid import uuid4


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
class VisualizationAsset:
    """Whitelisted visualization metadata discovered beneath one run root."""

    asset_id: str
    relative_path: str
    media_type: str
    width: int
    height: int
    alt_text: str
    caption: str
    scope_note: str
    axis_note: str


@dataclass(frozen=True, slots=True)
class RunResult:
    """Result data and generated files returned by an adapter."""

    rows: tuple[ConfigurationRow, ...]
    artifact_dir: Path
    source_version: str
    visualizations: tuple[VisualizationAsset, ...] = ()


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
        (output_dir / "pareto_frontier.png").write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000d49444154789c6360f8cfc000000301010018dd8db40000000049454e44ae426082"
            )
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
        return RunResult(
            rows=(row,),
            artifact_dir=output_dir,
            source_version=self.source_version,
            visualizations=(
                VisualizationAsset(
                    asset_id=uuid4().hex,
                    relative_path="pareto_frontier.png",
                    media_type="image/png",
                    width=1,
                    height=1,
                    alt_text="Pareto frontier visualization from the completed estimate.",
                    caption="AIConfigurator Pareto frontier from this completed run.",
                    scope_note=(
                        "Generated from the same sweep; the ranked table remains the exact-value "
                        "fallback."
                    ),
                    axis_note=(
                        "Use the generated axes and labels for visual trade-offs; use the table "
                        "for exact values."
                    ),
                ),
            ),
        )
