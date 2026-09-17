"""Server-owned comparison of the independently ranked serving modes."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from portal.adapters import ConfigurationRow

COMPARISON_METRICS: Final[tuple[tuple[str, str], ...]] = (
    ("tokens/s", "tokens/s"),
    ("ttft", "ms"),
    ("tpot", "ms"),
    ("num_total_gpus", "GPUs"),
)
DELTA_DEFINITION: Final[str] = (
    "disagg - agg; percentage = (disagg - agg) / abs(agg) * 100; "
    "deltas are rounded half-up to two decimal places"
)


@dataclass(frozen=True, slots=True)
class ComparisonMetric:
    """Comparison values for one required estimate metric."""

    name: str
    unit: str
    agg_value: float | int | None
    disagg_value: float | int | None
    absolute_delta: float | None
    percentage_delta: float | None
    unavailable_reason: str | None

    def to_payload(self) -> dict[str, object]:
        """Return the stable JSON representation used by the HTTP API."""

        return {
            "name": self.name,
            "unit": self.unit,
            "agg_value": self.agg_value,
            "disagg_value": self.disagg_value,
            "absolute_delta": self.absolute_delta,
            "percentage_delta": self.percentage_delta,
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True, slots=True)
class ComparisonSummary:
    """Comparison of rank-one rows from both serving modes."""

    available: bool
    agg_rank: int | None
    disagg_rank: int | None
    agg_metrics: Mapping[str, float | int] | None
    disagg_metrics: Mapping[str, float | int] | None
    metrics: tuple[ComparisonMetric, ...]
    unavailable_reason: str | None

    def to_payload(self) -> dict[str, object]:
        """Return the additive completed-run comparison contract."""

        return {
            "available": self.available,
            "baseline_mode": "agg",
            "candidate_mode": "disagg",
            "delta_definition": DELTA_DEFINITION,
            "unavailable_reason": self.unavailable_reason,
            "modes": {
                "agg": _mode_payload(self.agg_rank, self.agg_metrics),
                "disagg": _mode_payload(self.disagg_rank, self.disagg_metrics),
            },
            "metrics": [metric.to_payload() for metric in self.metrics],
        }


def build_comparison(rows: Sequence[ConfigurationRow]) -> ComparisonSummary:
    """Compare independently ranked rank-one ``agg`` and ``disagg`` rows.

    The SDK's mode frames are ranked independently. This function therefore never
    compares rows by their position in the flattened result or by a cross-mode
    rank. Missing values remain explicit and do not become zeroes.
    """

    agg_row = _rank_one(rows, "agg")
    disagg_row = _rank_one(rows, "disagg")
    agg_metrics = _numeric_metrics(agg_row)
    disagg_metrics = _numeric_metrics(disagg_row)

    reasons: list[str] = []
    if agg_row is None:
        reasons.append("agg rank 1 is unavailable")
    if disagg_row is None:
        reasons.append("disagg rank 1 is unavailable")

    comparison_metrics: list[ComparisonMetric] = []
    for metric_name, unit in COMPARISON_METRICS:
        agg_value = agg_metrics.get(metric_name) if agg_metrics is not None else None
        disagg_value = disagg_metrics.get(metric_name) if disagg_metrics is not None else None
        reason: str | None = None
        absolute_delta: float | None = None
        percentage_delta: float | None = None

        if agg_row is None:
            reason = "agg rank 1 is unavailable"
        elif disagg_row is None:
            reason = "disagg rank 1 is unavailable"
        elif agg_value is None:
            reason = "agg value is missing"
        elif disagg_value is None:
            reason = "disagg value is missing"
        else:
            absolute_delta = _round_delta(float(disagg_value) - float(agg_value))
            if float(agg_value) == 0:
                reason = "percentage delta unavailable because agg value is zero"
            else:
                percentage_delta = _round_delta(
                    (float(disagg_value) - float(agg_value)) / abs(float(agg_value)) * 100
                )

        if reason is not None and reason not in reasons:
            reasons.append(reason)
        comparison_metrics.append(
            ComparisonMetric(
                name=metric_name,
                unit=unit,
                agg_value=agg_value,
                disagg_value=disagg_value,
                absolute_delta=absolute_delta,
                percentage_delta=percentage_delta,
                unavailable_reason=reason,
            )
        )

    return ComparisonSummary(
        available=not reasons,
        agg_rank=agg_row.rank if agg_row is not None else None,
        disagg_rank=disagg_row.rank if disagg_row is not None else None,
        agg_metrics=agg_metrics,
        disagg_metrics=disagg_metrics,
        metrics=tuple(comparison_metrics),
        unavailable_reason="; ".join(reasons) if reasons else None,
    )


def _rank_one(rows: Sequence[ConfigurationRow], mode: str) -> ConfigurationRow | None:
    """Find the independently ranked top row for one serving mode."""

    return next((row for row in rows if row.serving_mode == mode and row.rank == 1), None)


def _numeric_metrics(row: ConfigurationRow | None) -> dict[str, float | int] | None:
    """Extract finite numeric values without coercing missing or text values."""

    if row is None:
        return None
    values: dict[str, float | int] = {}
    for name, _ in COMPARISON_METRICS:
        value = row.metrics.get(name)
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            continue
        if not math.isfinite(float(value)):
            continue
        values[name] = value
    return values


def _round_delta(value: float) -> float:
    """Round deltas deterministically for a stable API and browser display."""

    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _mode_payload(
    rank: int | None, metrics: Mapping[str, float | int] | None
) -> dict[str, object] | None:
    """Serialize a mode while preserving its rank and available values."""

    if rank is None or metrics is None:
        return None
    return {"rank": rank, "metrics": dict(metrics)}
