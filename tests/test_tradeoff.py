"""Trade-off surface normalization tests."""

from dataclasses import dataclass

import pytest

from portal.tradeoff import normalize_tradeoff_surface


@dataclass
class Frame:
    columns: tuple[str, ...]
    records: list[dict[str, float]]

    def to_dict(self, *, orient: str) -> list[dict[str, float]]:
        assert orient == "records"
        return self.records


def _frame(*rows: tuple[float, float]) -> Frame:
    return Frame(
        columns=("request_latency", "tokens/s/gpu_cluster"),
        records=[
            {"request_latency": latency, "tokens/s/gpu_cluster": throughput}
            for latency, throughput in rows
        ],
    )


def test_normalization_marks_cross_mode_dominance_and_preserves_objectives() -> None:
    surface = normalize_tradeoff_surface(
        {
            "agg": _frame((20_000, 5_000), (24_000, 8_000)),
            "disagg": _frame((22_000, 4_000), (30_000, 12_000)),
        }
    )

    assert surface is not None
    assert surface.source_modes == ("agg", "disagg")
    assert len(surface.frontier) == 3
    by_id = {point.candidate_id: point for point in surface.points}
    assert by_id["agg-1"].is_frontier is True
    assert by_id["agg-2"].is_frontier is True
    assert by_id["disagg-1"].is_frontier is False
    assert by_id["disagg-2"].is_frontier is True
    assert [point.candidate_id for point in surface.frontier] == [
        "agg-1",
        "agg-2",
        "disagg-2",
    ]


def test_normalization_rejects_missing_or_non_finite_required_values() -> None:
    missing = Frame(columns=("request_latency",), records=[])
    assert normalize_tradeoff_surface({"agg": missing}) is None
    assert normalize_tradeoff_surface({"agg": _frame((20_000, float("nan")))}) is None


def test_normalization_ignores_empty_mode_but_rejects_empty_union() -> None:
    empty = Frame(columns=("request_latency", "tokens/s/gpu_cluster"), records=[])
    assert normalize_tradeoff_surface({"agg": empty, "disagg": _frame((20_000, 5_000))})
    assert normalize_tradeoff_surface({"agg": empty}) is None


def test_normalization_rejects_unbounded_source() -> None:
    with pytest.raises(ValueError):
        normalize_tradeoff_surface({}, max_points=0)
    assert (
        normalize_tradeoff_surface({"agg": _frame((20_000, 5_000), (21_000, 6_000))}, max_points=1)
        is None
    )


def test_payload_includes_explicit_axis_directions() -> None:
    surface = normalize_tradeoff_surface({"agg": _frame((20_000, 5_000))})
    assert surface is not None
    payload = surface.to_payload()
    assert payload["x_direction"] == "lower is better"
    assert payload["y_direction"] == "higher is better"
    assert payload["candidate_scope"] == "union of complete per-mode SDK frontiers"
    assert payload["candidate_count"] == 1
