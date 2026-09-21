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


def test_topology_uses_rank_one_and_maps_workers_to_pods() -> None:
    comparison = build_comparison(
        (
            _row(
                2,
                "agg",
                **{"tp": 99, "pp": 99, "dp": 99, "num_total_gpus": 99, "parallel": "wrong"},
            ),
            _row(
                1,
                "agg",
                **{"tp": 4, "pp": 1, "dp": 1, "num_total_gpus": 4, "parallel": "tp4pp1dp1"},
            ),
            _row(
                1,
                "disagg",
                **{"(p)worker": 4, "(d)worker": 1, "(p)tp": 1, "(d)tp": 4},
            ),
        )
    )

    topology = comparison.to_payload()["topology"]
    assert topology["available"] is True
    agg_fields = {field["name"]: field for field in topology["modes"]["agg"]["fields"]}
    assert agg_fields["tp"]["value"] == 4
    assert agg_fields["parallel"]["value"] == "tp4pp1dp1"
    assert "(p)worker" not in agg_fields
    assert topology["modes"]["agg"]["kubernetes"]["available"] is False
    assert "cannot be derived" in topology["modes"]["agg"]["kubernetes"]["unavailable_reason"]

    disagg_fields = {field["name"]: field for field in topology["modes"]["disagg"]["fields"]}
    assert disagg_fields["(p)worker"]["value"] == 4
    assert disagg_fields["(p)tp"]["value"] == 1

    sizing = topology["modes"]["disagg"]["kubernetes"]
    assert sizing["prefill"]["replicas"] == 4
    assert sizing["prefill"]["gpus_per_pod"] == 1
    assert sizing["prefill"]["total_gpus"] == 4
    assert sizing["decode"]["replicas"] == 1
    assert sizing["decode"]["gpus_per_pod"] == 4
    assert sizing["decode"]["total_gpus"] == 4


def test_topology_preserves_missing_and_invalid_values() -> None:
    comparison = build_comparison(
        (
            _row(
                1,
                "agg",
                **{"tp": 4, "pp": 1, "dp": 1, "num_total_gpus": 4, "parallel": "tp4pp1dp1"},
            ),
            ConfigurationRow(
                rank=1,
                serving_mode="disagg",
                metrics={"(p)worker": "four", "(d)worker": 1, "(d)tp": 4},
            ),
        )
    )

    topology = comparison.to_payload()["topology"]
    assert topology["available"] is False
    fields = {field["name"]: field for field in topology["modes"]["disagg"]["fields"]}
    assert fields["(p)worker"]["unavailable_reason"] == "disagg value for (p)worker is invalid"
    assert topology["modes"]["disagg"]["kubernetes"]["prefill"]["replicas"] is None
    assert topology["modes"]["disagg"]["kubernetes"]["prefill"]["unavailable_reason"] == (
        "(p)worker must be a positive integer"
    )
