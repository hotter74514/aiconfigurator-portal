"""Server-owned aggregated/disaggregated comparison tests."""

from portal.adapters import ConfigurationRow
from portal.comparison import build_comparison


def _row(rank: int, mode: str, **metrics: float | int) -> ConfigurationRow:
    return ConfigurationRow(rank=rank, serving_mode=mode, metrics=metrics)


def test_comparison_uses_rank_one_and_signed_deltas() -> None:
    comparison = build_comparison(
        (
            _row(2, "agg", **{"tokens/s": 999, "ttft": 99, "tpot": 9, "num_total_gpus": 2}),
            _row(1, "agg", **{"tokens/s": 100, "ttft": 10, "tpot": 5, "num_total_gpus": 4}),
            _row(2, "disagg", **{"tokens/s": 1, "ttft": 99, "tpot": 9, "num_total_gpus": 2}),
            _row(
                1,
                "disagg",
                **{"tokens/s": 150, "ttft": 8, "tpot": 4, "num_total_gpus": 8},
            ),
        )
    )

    assert comparison.available is True
    payload = comparison.to_payload()
    assert payload["modes"]["agg"]["rank"] == 1
    assert payload["modes"]["agg"]["metrics"]["tokens/s"] == 100

    metrics = {metric["name"]: metric for metric in payload["metrics"]}
    assert metrics["tokens/s"]["absolute_delta"] == 50.0
    assert metrics["tokens/s"]["percentage_delta"] == 50.0
    assert metrics["ttft"]["absolute_delta"] == -2.0
    assert metrics["ttft"]["percentage_delta"] == -20.0
    assert metrics["num_total_gpus"]["absolute_delta"] == 4.0
    assert metrics["num_total_gpus"]["percentage_delta"] == 100.0


def test_comparison_rounds_percentage_half_up() -> None:
    comparison = build_comparison(
        (
            _row(1, "agg", **{"tokens/s": 3, "ttft": 1, "tpot": 1, "num_total_gpus": 1}),
            _row(1, "disagg", **{"tokens/s": 4, "ttft": 1, "tpot": 1, "num_total_gpus": 1}),
        )
    )

    metric = next(
        metric for metric in comparison.to_payload()["metrics"] if metric["name"] == "tokens/s"
    )
    assert metric["percentage_delta"] == 33.33
    assert metric["unit"] == "tokens/s"


def test_comparison_preserves_missing_mode_and_metric_reasons() -> None:
    comparison = build_comparison(
        (_row(1, "agg", **{"tokens/s": 100, "ttft": 10, "num_total_gpus": 4}),)
    )

    payload = comparison.to_payload()
    assert comparison.available is False
    assert payload["modes"]["disagg"] is None
    assert "disagg rank 1 is unavailable" in payload["unavailable_reason"]
    metrics = {metric["name"]: metric for metric in payload["metrics"]}
    assert metrics["tokens/s"]["disagg_value"] is None
    assert metrics["tokens/s"]["unavailable_reason"] == "disagg rank 1 is unavailable"

    missing_value = build_comparison(
        (
            _row(1, "agg", **{"tokens/s": 100, "ttft": 10, "num_total_gpus": 4}),
            _row(1, "disagg", **{"tokens/s": 120, "ttft": 9, "tpot": 2, "num_total_gpus": 4}),
        )
    )
    missing_metrics = {metric["name"]: metric for metric in missing_value.to_payload()["metrics"]}
    assert missing_metrics["tpot"]["unavailable_reason"] == "agg value is missing"


def test_comparison_marks_zero_baseline_percentage_unavailable() -> None:
    comparison = build_comparison(
        (
            _row(1, "agg", **{"tokens/s": 0, "ttft": 10, "tpot": 1, "num_total_gpus": 1}),
            _row(1, "disagg", **{"tokens/s": 5, "ttft": 10, "tpot": 1, "num_total_gpus": 1}),
        )
    )

    metric = next(
        metric for metric in comparison.to_payload()["metrics"] if metric["name"] == "tokens/s"
    )
    assert metric["absolute_delta"] == 5.0
    assert metric["percentage_delta"] is None
    assert metric["unavailable_reason"] == "percentage delta unavailable because agg value is zero"
