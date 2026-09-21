"""Stable adapter boundary around version-specific AIConfigurator behavior."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from portal.tradeoff import TradeoffPoint, TradeoffSurface


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
    tradeoff_surface: TradeoffSurface | None = None


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
        common_metrics: dict[str, float | int | str] = {
            "model": request.model,
            "system": request.system,
            "tokens/s/gpu": 1.0 / request.total_gpus,
            "num_total_gpus": request.total_gpus,
        }
        agg_row = ConfigurationRow(
            rank=1,
            serving_mode="agg",
            metrics={
                **common_metrics,
                "tokens/s": 1.0,
                "ttft": request.ttft_ms,
                "tpot": request.tpot_ms,
                "(p)worker": 1,
                "(d)worker": 1,
                "(p)tp": 16,
                "(d)tp": 16,
            },
        )
        disagg_row = ConfigurationRow(
            rank=1,
            serving_mode="disagg",
            metrics={
                **common_metrics,
                "tokens/s": 2.0,
                "ttft": request.ttft_ms + 1.0,
                "tpot": max(request.tpot_ms - 1.0, 0.001),
                "(p)worker": 4,
                "(d)worker": 1,
                "(p)tp": 4,
                "(d)tp": 16,
            },
        )
        fixture_points = (
            TradeoffPoint("agg-1", "agg", 1, 22_000.0, 2_800.0, True),
            TradeoffPoint("agg-2", "agg", 2, 24_500.0, 5_200.0, True),
            TradeoffPoint("disagg-1", "disagg", 1, 28_000.0, 4_100.0, False),
            TradeoffPoint("disagg-2", "disagg", 2, 30_000.0, 8_700.0, True),
        )
        tradeoff_surface = TradeoffSurface(
            points=fixture_points,
            frontier=(fixture_points[0], fixture_points[1], fixture_points[3]),
            source_modes=("agg", "disagg"),
        )
        return RunResult(
            rows=(agg_row, disagg_row),
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
            tradeoff_surface=tradeoff_surface,
        )
