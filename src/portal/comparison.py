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
TOPOLOGY_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("(p)worker", "Prefill workers"),
    ("(d)worker", "Decode workers"),
    ("(p)tp", "Prefill TP"),
    ("(d)tp", "Decode TP"),
)
KUBERNETES_WORKLOADS: Final[tuple[tuple[str, str, str], ...]] = (
    ("prefill", "(p)worker", "(p)tp"),
    ("decode", "(d)worker", "(d)tp"),
)
DELTA_DEFINITION: Final[str] = (
    "disagg - agg; percentage = (disagg - agg) / abs(agg) * 100; "
    "deltas are rounded half-up to two decimal places"
)
KUBERNETES_PRINCIPLE: Final[str] = (
    "Worker count determines pod replicas; TP determines GPUs required by each worker pod."
)
KUBERNETES_NETWORK_GUIDANCE: Final[tuple[str, ...]] = (
    "Use the lowest-latency, highest-bandwidth path available for prefill-to-decode "
    "KV-cache transfer.",
    "Same-node placement is only beneficial when the serving runtime can use the "
    "node's GPU interconnect or shared-memory path; otherwise use the supported "
    "high-speed network fabric.",
)
KUBERNETES_SCHEDULING_GUIDANCE: Final[tuple[str, ...]] = (
    "Keep every TP worker's GPUs on one topology-compatible node; use node labels "
    "and required or preferred affinity to express the constraint.",
    "Spread independent prefill replicas when throughput and failure isolation "
    "matter; do not force every prefill and decode pod onto one node by default.",
    "Set each workload's nvidia.com/gpu limit to its TP value and validate the "
    "generated estimate with a real cluster benchmark.",
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
    topology: "TopologySummary"
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
            "topology": self.topology.to_payload(),
        }


@dataclass(frozen=True, slots=True)
class KubernetesSizing:
    """Derived Kubernetes sizing for one prefill or decode worker class."""

    workload: str
    worker_field: str
    tp_field: str
    replicas: int | None
    gpus_per_pod: int | None
    total_gpus: int | None
    unavailable_reason: str | None

    def to_payload(self) -> dict[str, object]:
        """Return structured sizing without hiding incomplete source values."""

        return {
            "workload": self.workload,
            "worker_field": self.worker_field,
            "tp_field": self.tp_field,
            "replicas": self.replicas,
            "gpus_per_pod": self.gpus_per_pod,
            "total_gpus": self.total_gpus,
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True, slots=True)
class TopologySummary:
    """Rank-one topology fields and Kubernetes deployment guidance."""

    available: bool
    agg_rank: int | None
    disagg_rank: int | None
    agg_metrics: Mapping[str, float | int] | None
    disagg_metrics: Mapping[str, float | int] | None
    metrics: tuple[ComparisonMetric, ...]
    kubernetes: Mapping[str, object]
    unavailable_reason: str | None

    def to_payload(self) -> dict[str, object]:
        """Return the additive topology contract for completed runs."""

        return {
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
            "modes": {
                "agg": _mode_payload(self.agg_rank, self.agg_metrics),
                "disagg": _mode_payload(self.disagg_rank, self.disagg_metrics),
            },
            "metrics": [metric.to_payload() for metric in self.metrics],
            "kubernetes": dict(self.kubernetes),
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
        topology=build_topology_summary(rows),
        unavailable_reason="; ".join(reasons) if reasons else None,
    )


def build_topology_summary(rows: Sequence[ConfigurationRow]) -> TopologySummary:
    """Build rank-one topology values and Kubernetes sizing guidance."""

    agg_row = _rank_one(rows, "agg")
    disagg_row = _rank_one(rows, "disagg")
    agg_metrics = _numeric_metrics_for(agg_row, tuple(name for name, _ in TOPOLOGY_FIELDS))
    disagg_metrics = _numeric_metrics_for(disagg_row, tuple(name for name, _ in TOPOLOGY_FIELDS))

    reasons: list[str] = []
    if agg_row is None:
        reasons.append("agg rank 1 is unavailable")
    if disagg_row is None:
        reasons.append("disagg rank 1 is unavailable")

    topology_metrics: list[ComparisonMetric] = []
    for metric_name, label in TOPOLOGY_FIELDS:
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
            reason = f"agg value for {metric_name} is missing"
        elif disagg_value is None:
            reason = f"disagg value for {metric_name} is missing"
        else:
            absolute_delta = _round_delta(float(disagg_value) - float(agg_value))
            if float(agg_value) == 0:
                reason = f"percentage delta unavailable because agg {metric_name} is zero"
            else:
                percentage_delta = _round_delta(
                    (float(disagg_value) - float(agg_value)) / abs(float(agg_value)) * 100
                )
        if reason is not None and reason not in reasons:
            reasons.append(reason)
        topology_metrics.append(
            ComparisonMetric(
                name=metric_name,
                unit=label,
                agg_value=agg_value,
                disagg_value=disagg_value,
                absolute_delta=absolute_delta,
                percentage_delta=percentage_delta,
                unavailable_reason=reason,
            )
        )

    kubernetes_modes = {
        mode: {
            workload: _build_kubernetes_sizing(row, workload, worker_field, tp_field).to_payload()
            for workload, worker_field, tp_field in KUBERNETES_WORKLOADS
        }
        for mode, row in (("agg", agg_row), ("disagg", disagg_row))
    }
    return TopologySummary(
        available=not reasons,
        agg_rank=agg_row.rank if agg_row is not None else None,
        disagg_rank=disagg_row.rank if disagg_row is not None else None,
        agg_metrics=agg_metrics,
        disagg_metrics=disagg_metrics,
        metrics=tuple(topology_metrics),
        kubernetes={
            "principle": KUBERNETES_PRINCIPLE,
            "modes": kubernetes_modes,
            "network": list(KUBERNETES_NETWORK_GUIDANCE),
            "scheduling": list(KUBERNETES_SCHEDULING_GUIDANCE),
        },
        unavailable_reason="; ".join(reasons) if reasons else None,
    )


def _rank_one(rows: Sequence[ConfigurationRow], mode: str) -> ConfigurationRow | None:
    """Find the independently ranked top row for one serving mode."""

    return next((row for row in rows if row.serving_mode == mode and row.rank == 1), None)


def _numeric_metrics(row: ConfigurationRow | None) -> dict[str, float | int] | None:
    """Extract finite numeric values without coercing missing or text values."""

    return _numeric_metrics_for(row, tuple(name for name, _ in COMPARISON_METRICS))


def _numeric_metrics_for(
    row: ConfigurationRow | None, names: tuple[str, ...]
) -> dict[str, float | int] | None:
    """Extract selected finite numeric values without coercing text values."""

    if row is None:
        return None
    values: dict[str, float | int] = {}
    for name in names:
        value = row.metrics.get(name)
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            continue
        if not math.isfinite(float(value)):
            continue
        values[name] = value
    return values


def _build_kubernetes_sizing(
    row: ConfigurationRow | None,
    workload: str,
    worker_field: str,
    tp_field: str,
) -> KubernetesSizing:
    """Map worker count to replicas and TP to GPUs per pod."""

    values = _numeric_metrics_for(row, (worker_field, tp_field))
    worker_value = values.get(worker_field) if values is not None else None
    tp_value = values.get(tp_field) if values is not None else None
    reason: str | None = None
    replicas = _positive_integer(worker_value)
    gpus_per_pod = _positive_integer(tp_value)
    if row is None:
        reason = "rank 1 is unavailable"
    elif replicas is None:
        reason = f"{worker_field} must be a positive integer"
    elif gpus_per_pod is None:
        reason = f"{tp_field} must be a positive integer"
    total_gpus = (
        replicas * gpus_per_pod if replicas is not None and gpus_per_pod is not None else None
    )
    return KubernetesSizing(
        workload=workload,
        worker_field=worker_field,
        tp_field=tp_field,
        replicas=replicas,
        gpus_per_pod=gpus_per_pod,
        total_gpus=total_gpus,
        unavailable_reason=reason,
    )


def _positive_integer(value: float | int | None) -> int | None:
    """Return a positive integer-valued number, preserving invalid values as missing."""

    if value is None or float(value) <= 0 or not float(value).is_integer():
        return None
    return int(value)


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
