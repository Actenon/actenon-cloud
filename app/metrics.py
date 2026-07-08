from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Literal

DEFAULT_HISTOGRAM_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)

MetricType = Literal["counter", "gauge", "histogram"]
LabelKey = tuple[tuple[str, str], ...]
_METRICS_LOCK = Lock()
_METRICS_REGISTRY: MetricsRegistry | None = None


def _freeze_labels(label_names: tuple[str, ...], labels: dict[str, str]) -> LabelKey:
    if set(labels) != set(label_names):
        expected = ", ".join(label_names) or "<none>"
        actual = ", ".join(sorted(labels)) or "<none>"
        raise ValueError(
            f"metric labels do not match definition: expected {expected}; got {actual}"
        )
    return tuple((name, str(labels[name])) for name in label_names)


def _escape_help(value: str) -> str:
    return value.replace("\\", r"\\").replace("\n", r"\n")


def _escape_label_value(value: str) -> str:
    return value.replace("\\", r"\\").replace("\n", r"\n").replace('"', r"\"")


def _format_float(value: float) -> str:
    if value == float("inf"):
        return "+Inf"
    if value.is_integer():
        return str(int(value))
    return f"{value:.12g}"


def _format_sample(
    name: str,
    labels: LabelKey,
    value: float,
    *,
    extra_labels: tuple[tuple[str, str], ...] = (),
) -> str:
    all_labels = labels + extra_labels
    if not all_labels:
        return f"{name} {_format_float(value)}"
    formatted_labels = ",".join(
        f'{label_name}="{_escape_label_value(label_value)}"'
        for label_name, label_value in all_labels
    )
    return f"{name}{{{formatted_labels}}} {_format_float(value)}"


@dataclass(slots=True)
class MetricDefinition:
    name: str
    description: str
    kind: MetricType
    label_names: tuple[str, ...]


class CounterMetric:
    def __init__(self, definition: MetricDefinition, lock: Lock) -> None:
        self.definition = definition
        self._lock = lock
        self._values: defaultdict[LabelKey, float] = defaultdict(float)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        frozen = _freeze_labels(self.definition.label_names, labels)
        with self._lock:
            self._values[frozen] += amount

    def render(self) -> list[str]:
        lines = [
            f"# HELP {self.definition.name} {_escape_help(self.definition.description)}",
            f"# TYPE {self.definition.name} counter",
        ]
        with self._lock:
            samples = sorted(self._values.items())
        if not samples:
            if not self.definition.label_names:
                lines.append(_format_sample(self.definition.name, (), 0.0))
            return lines
        for labels, value in samples:
            lines.append(_format_sample(self.definition.name, labels, value))
        return lines


class GaugeMetric:
    def __init__(self, definition: MetricDefinition, lock: Lock) -> None:
        self.definition = definition
        self._lock = lock
        self._values: defaultdict[LabelKey, float] = defaultdict(float)

    def set(self, value: float, **labels: str) -> None:
        frozen = _freeze_labels(self.definition.label_names, labels)
        with self._lock:
            self._values[frozen] = value

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        frozen = _freeze_labels(self.definition.label_names, labels)
        with self._lock:
            self._values[frozen] += amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        self.inc(-amount, **labels)

    def render(self) -> list[str]:
        lines = [
            f"# HELP {self.definition.name} {_escape_help(self.definition.description)}",
            f"# TYPE {self.definition.name} gauge",
        ]
        with self._lock:
            samples = sorted(self._values.items())
        if not samples:
            if not self.definition.label_names:
                lines.append(_format_sample(self.definition.name, (), 0.0))
            return lines
        for labels, value in samples:
            lines.append(_format_sample(self.definition.name, labels, value))
        return lines


class HistogramMetric:
    def __init__(
        self,
        definition: MetricDefinition,
        lock: Lock,
        *,
        buckets: tuple[float, ...] = DEFAULT_HISTOGRAM_BUCKETS,
    ) -> None:
        self.definition = definition
        self._lock = lock
        self._buckets = tuple(sorted(buckets))
        self._bucket_counts: defaultdict[LabelKey, dict[float, int]] = defaultdict(
            lambda: {bucket: 0 for bucket in self._buckets}
        )
        self._counts: defaultdict[LabelKey, int] = defaultdict(int)
        self._sums: defaultdict[LabelKey, float] = defaultdict(float)

    def observe(self, value: float, **labels: str) -> None:
        frozen = _freeze_labels(self.definition.label_names, labels)
        with self._lock:
            self._counts[frozen] += 1
            self._sums[frozen] += value
            for bucket in self._buckets:
                if value <= bucket:
                    self._bucket_counts[frozen][bucket] += 1

    def render(self) -> list[str]:
        lines = [
            f"# HELP {self.definition.name} {_escape_help(self.definition.description)}",
            f"# TYPE {self.definition.name} histogram",
        ]
        with self._lock:
            label_sets = sorted(set(self._counts) | set(self._bucket_counts) | set(self._sums))
            bucket_counts = {
                labels: dict(self._bucket_counts[labels])
                for labels in label_sets
            }
            counts = {labels: self._counts[labels] for labels in label_sets}
            sums = {labels: self._sums[labels] for labels in label_sets}
        if not label_sets and self.definition.label_names:
            return lines
        if not label_sets:
            label_sets = [()]
            bucket_counts = {(): {bucket: 0 for bucket in self._buckets}}
            counts = {(): 0}
            sums = {(): 0.0}
        for labels in label_sets:
            # Prometheus histograms require *cumulative* bucket counts: each
            # `_bucket{le="X"}` sample must be the number of observations with
            # value <= X. `observe()` already stores cumulative counts (it
            # increments every bucket whose upper bound is >= value), so each
            # bucket value is emitted directly. Summing them here would
            # double-count and break monotonicity.
            for bucket in self._buckets:
                cumulative = bucket_counts[labels].get(bucket, 0)
                lines.append(
                    _format_sample(
                        f"{self.definition.name}_bucket",
                        labels,
                        float(cumulative),
                        extra_labels=(("le", _format_float(bucket)),),
                    )
                )
            lines.append(
                _format_sample(
                    f"{self.definition.name}_bucket",
                    labels,
                    float(counts[labels]),
                    extra_labels=(("le", "+Inf"),),
                )
            )
            lines.append(_format_sample(f"{self.definition.name}_sum", labels, sums[labels]))
            lines.append(
                _format_sample(
                    f"{self.definition.name}_count",
                    labels,
                    float(counts[labels]),
                )
            )
        return lines


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._metrics: dict[str, CounterMetric | GaugeMetric | HistogramMetric] = {}
        self._definitions: dict[str, MetricDefinition] = {}

    def counter(
        self,
        name: str,
        description: str,
        *,
        label_names: tuple[str, ...] = (),
    ) -> CounterMetric:
        definition = MetricDefinition(name, description, "counter", label_names)
        metric = self._metrics.get(name)
        if metric is not None:
            self._ensure_compatible(definition)
            return metric  # type: ignore[return-value]
        counter = CounterMetric(definition, self._lock)
        self._register(definition, counter)
        return counter

    def gauge(
        self,
        name: str,
        description: str,
        *,
        label_names: tuple[str, ...] = (),
    ) -> GaugeMetric:
        definition = MetricDefinition(name, description, "gauge", label_names)
        metric = self._metrics.get(name)
        if metric is not None:
            self._ensure_compatible(definition)
            return metric  # type: ignore[return-value]
        gauge = GaugeMetric(definition, self._lock)
        self._register(definition, gauge)
        return gauge

    def histogram(
        self,
        name: str,
        description: str,
        *,
        label_names: tuple[str, ...] = (),
        buckets: tuple[float, ...] = DEFAULT_HISTOGRAM_BUCKETS,
    ) -> HistogramMetric:
        definition = MetricDefinition(name, description, "histogram", label_names)
        metric = self._metrics.get(name)
        if metric is not None:
            self._ensure_compatible(definition)
            return metric  # type: ignore[return-value]
        histogram = HistogramMetric(definition, self._lock, buckets=buckets)
        self._register(definition, histogram)
        return histogram

    def render_prometheus(self) -> str:
        lines: list[str] = []
        for name in sorted(self._metrics):
            lines.extend(self._metrics[name].render())
        return "\n".join(lines) + "\n"

    def _register(
        self,
        definition: MetricDefinition,
        metric: CounterMetric | GaugeMetric | HistogramMetric,
    ) -> None:
        self._definitions[definition.name] = definition
        self._metrics[definition.name] = metric

    def _ensure_compatible(self, definition: MetricDefinition) -> None:
        existing = self._definitions[definition.name]
        if existing != definition:
            raise ValueError(
                f"metric '{definition.name}' already registered with a different definition"
            )


def get_metrics_registry() -> MetricsRegistry:
    global _METRICS_REGISTRY
    with _METRICS_LOCK:
        if _METRICS_REGISTRY is None:
            _METRICS_REGISTRY = MetricsRegistry()
        return _METRICS_REGISTRY


def reset_metrics_registry() -> MetricsRegistry:
    global _METRICS_REGISTRY
    with _METRICS_LOCK:
        _METRICS_REGISTRY = MetricsRegistry()
        return _METRICS_REGISTRY


def initialize_runtime_metrics() -> MetricsRegistry:
    registry = get_metrics_registry()
    registry.counter(
        "action_control_plane_http_requests_total",
        "Count of completed HTTP requests served by the app runtime.",
        label_names=("method", "path_template", "status_code"),
    )
    registry.histogram(
        "action_control_plane_http_request_duration_seconds",
        "HTTP request duration in seconds by method, path template, and response status.",
        label_names=("method", "path_template", "status_code"),
    )
    registry.gauge(
        "action_control_plane_http_requests_in_progress",
        "Current number of in-flight HTTP requests handled by the app runtime.",
    )
    registry.gauge(
        "action_control_plane_runtime_ready",
        "Whether the current runtime instance is ready to accept pilot traffic.",
    )
    registry.gauge(
        "action_control_plane_dependency_ready",
        "Dependency readiness status for runtime checks.",
        label_names=("check_name",),
    )
    registry.gauge(
        "action_control_plane_runtime_info",
        "Static metadata about the running Actenon Cloud control-plane instance.",
        label_names=(
            "service",
            "environment",
            "version",
            "auth_mode",
            "capability_release_mode",
        ),
    )
    registry.gauge(
        "action_control_plane_process_started_time_seconds",
        "Unix timestamp at which this runtime instance started.",
    )
    registry.counter(
        "action_control_plane_action_intake_total",
        "Action Intent intake results by control decision and contract status.",
        label_names=("decision_state", "contract_validation_status", "idempotent_replay"),
    )
    registry.counter(
        "action_control_plane_approval_decisions_total",
        "Approval decisions recorded by decision and resulting approval status.",
        label_names=("decision", "approval_status"),
    )
    registry.counter(
        "action_control_plane_evidence_mutations_total",
        "Evidence mutations by operation, evidence type, storage mode, and status.",
        label_names=("operation", "evidence_type", "storage_mode", "status"),
    )
    registry.counter(
        "action_control_plane_proof_issuance_total",
        "Proof issuance attempts by resulting proof status, proof kind, and replay status.",
        label_names=("proof_status", "proof_kind", "idempotent_replay"),
    )
    registry.counter(
        "action_control_plane_receipt_ingestions_total",
        "Receipt ingestions by receipt state, contract validation status, outcome, and replay.",
        label_names=("receipt_state", "contract_validation_status", "outcome", "idempotent_replay"),
    )
    registry.counter(
        "action_control_plane_transparency_log_leaves_total",
        "Receipt digests appended to transparency logs.",
        label_names=("log_id",),
    )
    registry.counter(
        "action_control_plane_transparency_checkpoints_total",
        "Transparency checkpoints published by log and key identifier.",
        label_names=("log_id", "key_id"),
    )
    registry.gauge(
        "action_control_plane_transparency_tree_size",
        "Latest published transparency-log tree size.",
        label_names=("log_id",),
    )
    registry.counter(
        "action_control_plane_transparency_integrity_failures_total",
        "Detected transparency-log integrity failures.",
        label_names=("log_id",),
    )
    return registry


def set_process_started_at(timestamp_seconds: float | None = None) -> None:
    started_at = timestamp_seconds if timestamp_seconds is not None else time()
    get_metrics_registry().gauge(
        "action_control_plane_process_started_time_seconds",
        "Unix timestamp at which this runtime instance started.",
    ).set(started_at)
