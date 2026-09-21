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
AGGREGATED_TOPOLOGY_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("tp", "Tensor parallel width"),
    ("pp", "Pipeline parallel width"),
    ("dp", "Data parallel width"),
    ("num_total_gpus", "Allocated GPUs"),
    ("parallel", "Parallel layout"),
)
DISAGGREGATED_TOPOLOGY_FIELDS: Final[tuple[tuple[str, str], ...]] = (
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
    "Disaggregated worker count determines Pod replicas; TP determines GPUs per worker Pod. "
    "Aggregated TP/PP/DP values describe parallelism, not Pod replicas."
)
KUBERNETES_NETWORK_GUIDANCE: Final[tuple[str, ...]] = (
    "Disaggregated serving needs the lowest-latency, highest-bandwidth path available "
    "for prefill-to-decode KV-cache transfer.",
    "Same-node placement is only beneficial when the serving runtime can use the "
    "node's GPU interconnect or shared-memory path; otherwise use the supported "
    "high-speed network fabric.",
)
KUBERNETES_SCHEDULING_GUIDANCE: Final[tuple[str, ...]] = (
    "For disaggregated TP workers, keep each worker's GPUs on one topology-compatible "
    "node; use node labels and required or preferred affinity.",
    "Do not infer an aggregated Pod count from tp or num_total_gpus; use an explicit "
    "deployment artifact or runtime contract.",
    "Set nvidia.com/gpu from the verified TP width only where the result identifies "
    "the worker group, then validate the estimate with a real cluster benchmark.",
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
class TopologyField:
    """One mode-specific source field preserved without cross-mode inference."""

    name: str
    label: str
    value: float | int | str | None
    unavailable_reason: str | None

    def to_payload(self) -> dict[str, object]:
        """Return the source value and an explicit missing-value reason."""

        return {
            "name": self.name,
            "label": self.label,
            "value": self.value,
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True, slots=True)
class ModeTopology:
    """Rank-one topology values for one serving mode."""

    rank: int | None
    fields: tuple[TopologyField, ...]
    kubernetes: Mapping[str, object]
    unavailable_reason: str | None

    def to_payload(self) -> dict[str, object]:
        """Return one mode's topology and mode-specific deployment meaning."""

        return {
            "rank": self.rank,
            "fields": [field.to_payload() for field in self.fields],
            "kubernetes": dict(self.kubernetes),
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True, slots=True)
class TopologySummary:
    """Mode-aware rank-one topology fields and Kubernetes guidance."""

    available: bool
    agg: ModeTopology
    disagg: ModeTopology
    kubernetes: Mapping[str, object]
    unavailable_reason: str | None

    def to_payload(self) -> dict[str, object]:
        """Return the mode-aware topology contract for completed runs."""

        return {
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
            "modes": {"agg": self.agg.to_payload(), "disagg": self.disagg.to_payload()},
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
    """Build source-faithful topology values and Kubernetes guidance."""

    agg = _build_mode_topology(_rank_one(rows, "agg"), "agg")
    disagg = _build_mode_topology(_rank_one(rows, "disagg"), "disagg")
    reasons = [reason for reason in (agg.unavailable_reason, disagg.unavailable_reason) if reason]
    return TopologySummary(
        available=not reasons,
        agg=agg,
        disagg=disagg,
        kubernetes={
            "principle": KUBERNETES_PRINCIPLE,
            "network": list(KUBERNETES_NETWORK_GUIDANCE),
            "scheduling": list(KUBERNETES_SCHEDULING_GUIDANCE),
        },
        unavailable_reason="; ".join(reasons) if reasons else None,
    )


def _build_mode_topology(row: ConfigurationRow | None, mode: str) -> ModeTopology:
    """Preserve only the fields documented for the selected serving mode."""

    definitions = AGGREGATED_TOPOLOGY_FIELDS if mode == "agg" else DISAGGREGATED_TOPOLOGY_FIELDS
    fields: list[TopologyField] = []
    reasons: list[str] = []
    for name, label in definitions:
        value = row.metrics.get(name) if row is not None else None
        reason = _topology_value_reason(value, name, mode, row is None)
        if reason is not None:
            reasons.append(reason)
        fields.append(TopologyField(name, label, value if reason is None else None, reason))

    kubernetes: dict[str, object]
    if mode == "agg":
        kubernetes = {
            "available": False,
            "prefill": None,
            "decode": None,
            "unavailable_reason": (
                "agg result does not expose worker or replica fields; Pod replicas "
                "cannot be derived from tp or num_total_gpus"
            ),
        }
    else:
        sizing = {
            workload: _build_kubernetes_sizing(row, workload, worker_field, tp_field).to_payload()
            for workload, worker_field, tp_field in KUBERNETES_WORKLOADS
        }
        sizing_reasons = [
            str(item["unavailable_reason"])
            for item in sizing.values()
            if item["unavailable_reason"] is not None
        ]
        kubernetes = {
            "available": not sizing_reasons,
            **sizing,
            "unavailable_reason": "; ".join(sizing_reasons) if sizing_reasons else None,
        }

    rank = row.rank if row is not None else None
    if row is None:
        reasons.insert(0, f"{mode} rank 1 is unavailable")
    return ModeTopology(
        rank=rank,
        fields=tuple(fields),
        kubernetes=kubernetes,
        unavailable_reason="; ".join(reasons) if reasons else None,
    )


def _topology_value_reason(
    value: float | int | str | None, name: str, mode: str, row_missing: bool
) -> str | None:
    """Validate one source topology value without inventing a replacement."""

    if row_missing:
        return f"{mode} rank 1 is unavailable"
    if value is None:
        return f"{mode} value for {name} is missing"
    if isinstance(value, bool):
        return f"{mode} value for {name} is invalid"
    if mode == "disagg" and not isinstance(value, (float, int)):
        return f"{mode} value for {name} is invalid"
    if mode == "agg" and name != "parallel" and not isinstance(value, (float, int)):
        return f"{mode} value for {name} is invalid"
    if isinstance(value, (float, int)) and not math.isfinite(float(value)):
        return f"{mode} value for {name} is not finite"
    if isinstance(value, str) and not value.strip():
        return f"{mode} value for {name} is blank"
    return None


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
