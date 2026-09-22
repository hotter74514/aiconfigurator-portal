"""Portal-owned, bounded trade-off surface data contract."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MAX_TRADEOFF_POINTS = 128
REQUIRED_COLUMNS = ("request_latency", "tokens/s/gpu_cluster")


@dataclass(frozen=True, slots=True)
class TradeoffPoint:
    """One complete SDK frontier candidate normalized for the browser."""

    candidate_id: str
    serving_mode: str
    rank: int
    latency_ms: float
    throughput_tokens_s: float
    is_frontier: bool

    def to_payload(self) -> dict[str, str | int | float | bool]:
        return {
            "id": self.candidate_id,
            "serving_mode": self.serving_mode,
            "rank": self.rank,
            "latency_ms": self.latency_ms,
            "throughput_tokens_s": self.throughput_tokens_s,
            "is_frontier": self.is_frontier,
        }


@dataclass(frozen=True, slots=True)
class TradeoffSurface:
    """A deterministic payload for rendering the latency/throughput surface."""

    points: tuple[TradeoffPoint, ...]
    frontier: tuple[TradeoffPoint, ...]
    source_modes: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "version": "tradeoff-surface-1",
            "x_label": "Request latency (ms)",
            "x_direction": "lower is better",
            "y_label": "Throughput (tokens/s)",
            "y_direction": "higher is better",
            "source": "AIConfigurator pareto_fronts",
            "candidate_scope": "union of complete per-mode SDK frontiers",
            "source_modes": list(self.source_modes),
            "candidate_count": len(self.points),
            "frontier_count": len(self.frontier),
            "points": [point.to_payload() for point in self.points],
            "frontier": [point.to_payload() for point in self.frontier],
        }


def normalize_tradeoff_surface(
    pareto_fronts: Mapping[str, Any], *, max_points: int = MAX_TRADEOFF_POINTS
) -> TradeoffSurface | None:
    """Normalize complete SDK frontier frames and classify cross-mode dominance.

    AIConfigurator exposes one complete frontier per serving mode. The portal
    treats their bounded union as the candidate set and marks a point dominated
    only when another complete-frame point is no slower and at least as fast.
    It never uses the normalized top-N result rows for this calculation.
    """

    if max_points < 1:
        raise ValueError("max_points must be positive")
    candidates: list[TradeoffPoint] = []
    source_modes: list[str] = []
    for mode, frame in sorted(pareto_fronts.items(), key=lambda item: str(item[0])):
        if frame is None or not hasattr(frame, "columns") or not hasattr(frame, "to_dict"):
            return None
        columns = {str(column) for column in frame.columns}
        if not set(REQUIRED_COLUMNS).issubset(columns):
            return None
        records = frame.to_dict(orient="records")
        if not records:
            continue
        mode_name = str(mode)
        source_modes.append(mode_name)
        for rank, record in enumerate(records, start=1):
            latency = _finite_number(record.get("request_latency"))
            throughput = _finite_number(record.get("tokens/s/gpu_cluster"))
            if latency is None or throughput is None:
                return None
            candidates.append(
                TradeoffPoint(
                    candidate_id=f"{mode_name}-{rank}",
                    serving_mode=mode_name,
                    rank=rank,
                    latency_ms=latency,
                    throughput_tokens_s=throughput,
                    is_frontier=False,
                )
            )
            if len(candidates) > max_points:
                return None

    if not candidates:
        return None

    frontier: list[TradeoffPoint] = []
    for point in candidates:
        if not any(_dominates(other, point) for other in candidates if other != point):
            frontier.append(point)
    frontier.sort(
        key=lambda point: (point.latency_ms, -point.throughput_tokens_s, point.candidate_id)
    )
    frontier_ids = {point.candidate_id for point in frontier}
    marked = tuple(
        TradeoffPoint(
            candidate_id=point.candidate_id,
            serving_mode=point.serving_mode,
            rank=point.rank,
            latency_ms=point.latency_ms,
            throughput_tokens_s=point.throughput_tokens_s,
            is_frontier=point.candidate_id in frontier_ids,
        )
        for point in candidates
    )
    marked_by_id = {point.candidate_id: point for point in marked}
    return TradeoffSurface(
        points=marked,
        frontier=tuple(marked_by_id[point.candidate_id] for point in frontier),
        source_modes=tuple(source_modes),
    )


def _finite_number(value: Any) -> float | None:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _dominates(left: TradeoffPoint, right: TradeoffPoint) -> bool:
    """Return whether left is no slower, no less productive, and strictly better."""

    no_slower = left.latency_ms <= right.latency_ms
    no_less_productive = left.throughput_tokens_s >= right.throughput_tokens_s
    strictly_better = (
        left.latency_ms < right.latency_ms or left.throughput_tokens_s > right.throughput_tokens_s
    )
    return no_slower and no_less_productive and strictly_better
