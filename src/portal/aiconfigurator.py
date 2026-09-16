"""Lazy, version-pinned AIConfigurator SDK adapter."""

import importlib.metadata
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from portal.adapters import ConfigurationRow, RunRequest, RunResult


def _scalar(value: Any) -> float | int | str | None:
    """Convert a DataFrame cell into a JSON-safe scalar."""

    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (bool, float, int, str)):
        return value
    return str(value)


def _normalize_rows(best_configs: Mapping[str, Any]) -> tuple[ConfigurationRow, ...]:
    """Normalize SDK DataFrames without exposing nested diagnostic payloads."""

    rows: list[ConfigurationRow] = []
    for mode, frame in best_configs.items():
        for index, record in enumerate(frame.to_dict(orient="records"), start=1):
            metrics = {
                str(key): normalized
                for key, value in record.items()
                if key != "_per_ops_source" and (normalized := _scalar(value)) is not None
            }
            rows.append(ConfigurationRow(rank=index, serving_mode=str(mode), metrics=metrics))
    return tuple(rows)


def run_ai_configurator(request: RunRequest, output_dir: str) -> RunResult:
    """Run one default sweep in a worker process.

    The import is intentionally inside the function: the published dependency is
    Linux x86-64 only and must not be imported by local ARM development tools.
    """

    from aiconfigurator.cli import cli_default  # type: ignore[import-not-found]

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    result = cli_default(
        model_path=request.model,
        total_gpus=request.total_gpus,
        system=request.system,
        ttft=request.ttft_ms,
        tpot=request.tpot_ms,
        isl=request.isl,
        osl=request.osl,
        strict_sla=True,
        top_n=5,
        save_dir=str(destination),
    )
    package_version = importlib.metadata.version("aiconfigurator")
    return RunResult(
        rows=_normalize_rows(result.best_configs),
        artifact_dir=destination,
        source_version=f"aiconfigurator-{package_version}",
    )
