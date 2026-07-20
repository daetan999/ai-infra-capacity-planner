"""Domain types and boundary validation for deterministic capacity sizing."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class WorkloadMode(StrEnum):
    LLM_TRAINING = "llm_training"
    LLM_INFERENCE = "llm_inference"
    RAG_INFERENCE = "rag_inference"
    VISION_INFERENCE = "vision_inference"
    BATCH_AI_HPC = "batch_ai_hpc"


class Precision(StrEnum):
    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    INT8 = "int8"
    INT4 = "int4"

    @property
    def bytes_per_parameter(self) -> float:
        return {
            Precision.FP32: 4.0,
            Precision.FP16: 2.0,
            Precision.BF16: 2.0,
            Precision.INT8: 1.0,
            Precision.INT4: 0.5,
        }[self]

    @property
    def work_factor(self) -> float:
        return {
            Precision.FP32: 1.8,
            Precision.FP16: 1.0,
            Precision.BF16: 1.0,
            Precision.INT8: 0.62,
            Precision.INT4: 0.42,
        }[self]

    @property
    def next_lower(self) -> Precision:
        return {
            Precision.FP32: Precision.FP16,
            Precision.FP16: Precision.INT8,
            Precision.BF16: Precision.INT8,
            Precision.INT8: Precision.INT4,
            Precision.INT4: Precision.INT4,
        }[self]


@dataclass(frozen=True, slots=True)
class AcceleratorProfile:
    profile_id: str
    name: str
    memory_gb: float
    theoretical_throughput: dict[str, float]
    throughput_unit: str
    derating_factor: float
    power_watts_min: float
    power_watts_max: float
    monthly_price_usd_min: float
    monthly_price_usd_max: float
    price_source_type: str
    illustrative: bool

    @classmethod
    def from_mapping(cls, profile_id: str, values: Mapping[str, Any]) -> AcceleratorProfile:
        throughput = {
            str(key): float(value)
            for key, value in _mapping(values, "theoretical_throughput").items()
        }
        expected_modes = {mode.value for mode in WorkloadMode}
        if set(throughput) != expected_modes or any(value <= 0 for value in throughput.values()):
            raise ValueError(
                f"Profile {profile_id} must define positive throughput for every workload mode"
            )

        power = _mapping(values, "power_watts")
        monthly_price = _mapping(values, "monthly_price_usd")
        profile = cls(
            profile_id=profile_id,
            name=str(values["name"]),
            memory_gb=float(values["memory_gb"]),
            theoretical_throughput=throughput,
            throughput_unit=str(values["throughput_unit"]),
            derating_factor=float(values["derating_factor"]),
            power_watts_min=float(power["min"]),
            power_watts_max=float(power["max"]),
            monthly_price_usd_min=float(monthly_price["min"]),
            monthly_price_usd_max=float(monthly_price["max"]),
            price_source_type=str(values["price_source_type"]),
            illustrative=bool(values["illustrative"]),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        if not self.profile_id.startswith("illustrative-") or not self.illustrative:
            raise ValueError("Accelerator profiles must be explicitly illustrative")
        if self.memory_gb <= 0:
            raise ValueError(f"Profile {self.profile_id} memory_gb must be positive")
        if not 0 < self.derating_factor < 1:
            raise ValueError(f"Profile {self.profile_id} derating_factor must be between 0 and 1")
        if not 0 < self.power_watts_min <= self.power_watts_max:
            raise ValueError(f"Profile {self.profile_id} power range is invalid")
        if not 0 < self.monthly_price_usd_min <= self.monthly_price_usd_max:
            raise ValueError(f"Profile {self.profile_id} monthly price range is invalid")

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.profile_id,
            "name": self.name,
            "memory_gb": self.memory_gb,
            "throughput_unit": self.throughput_unit,
            "illustrative": self.illustrative,
            "price_source_type": self.price_source_type,
        }


@dataclass(frozen=True, slots=True)
class SizingInputs:
    mode: WorkloadMode
    accelerator_profile: str
    model_parameters_billion: float
    precision: Precision
    context_tokens: float
    input_tokens: float
    output_tokens: float
    requests_per_second: float
    concurrent_users: float
    peak_multiplier: float
    latency_target_ms: float
    availability_target_pct: float
    dataset_tb: float
    training_window_hours: float
    storage_tb: float
    storage_growth_pct: float
    ingress_gb_per_day: float
    egress_gb_per_day: float
    region: str
    target_utilization_pct: float
    growth_pct: float
    batch_size: float
    missing_inputs: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> SizingInputs:
        values = _normalize_aliases(raw)
        mode_value = values.get("workload_mode", values.get("mode"))
        try:
            mode = WorkloadMode(str(mode_value))
        except ValueError as exc:
            supported = ", ".join(mode.value for mode in WorkloadMode)
            raise ValueError(
                f"Unsupported workload mode: {mode_value!r}. Choose one of: {supported}"
            ) from exc

        precision_value = values.get("precision", "fp16")
        try:
            precision = Precision(str(precision_value).lower())
        except ValueError as exc:
            supported = ", ".join(item.value for item in Precision)
            raise ValueError(
                f"Unsupported precision: {precision_value!r}. Choose one of: {supported}"
            ) from exc

        defaults: dict[str, float | str] = {
            "accelerator_profile": "illustrative-balanced",
            "model_parameters_billion": 13.0,
            "context_tokens": 4_096.0,
            "input_tokens": 750.0,
            "output_tokens": 250.0,
            "requests_per_second": 10.0,
            "concurrent_users": 50.0,
            "peak_multiplier": 1.5,
            "latency_target_ms": 1_500.0,
            "availability_target_pct": 99.5,
            "dataset_tb": 1.0,
            "training_window_hours": 168.0,
            "storage_tb": 5.0,
            "storage_growth_pct": 15.0,
            "ingress_gb_per_day": 100.0,
            "egress_gb_per_day": 100.0,
            "region": "unspecified",
            "target_utilization_pct": 65.0,
            "growth_pct": 15.0,
            "batch_size": 4.0,
        }
        numeric_fields = set(defaults) - {"accelerator_profile", "region"}
        normalized: dict[str, float | str] = {}
        for field, default in defaults.items():
            supplied = values.get(field, default)
            if field in numeric_fields:
                normalized[field] = _positive_number(field, supplied)
            else:
                normalized[field] = str(supplied).strip() or str(default)

        _validate_bounded_percent("target_utilization_pct", normalized, 20, 95)
        _validate_bounded_percent("availability_target_pct", normalized, 90, 100)
        if (
            mode in {WorkloadMode.LLM_TRAINING, WorkloadMode.BATCH_AI_HPC}
            and float(normalized["training_window_hours"]) == 0
        ):
            raise ValueError("training_window_hours must be greater than zero")
        required = required_input_fields(mode)
        missing = tuple(
            sorted(
                field
                for field in required
                if field not in values or _is_missing_evidence(values[field])
            )
        )
        return cls(
            mode=mode,
            accelerator_profile=str(normalized["accelerator_profile"]),
            model_parameters_billion=float(normalized["model_parameters_billion"]),
            precision=precision,
            context_tokens=float(normalized["context_tokens"]),
            input_tokens=float(normalized["input_tokens"]),
            output_tokens=float(normalized["output_tokens"]),
            requests_per_second=float(normalized["requests_per_second"]),
            concurrent_users=float(normalized["concurrent_users"]),
            peak_multiplier=float(normalized["peak_multiplier"]),
            latency_target_ms=float(normalized["latency_target_ms"]),
            availability_target_pct=float(normalized["availability_target_pct"]),
            dataset_tb=float(normalized["dataset_tb"]),
            training_window_hours=float(normalized["training_window_hours"]),
            storage_tb=float(normalized["storage_tb"]),
            storage_growth_pct=float(normalized["storage_growth_pct"]),
            ingress_gb_per_day=float(normalized["ingress_gb_per_day"]),
            egress_gb_per_day=float(normalized["egress_gb_per_day"]),
            region=str(normalized["region"]),
            target_utilization_pct=float(normalized["target_utilization_pct"]),
            growth_pct=float(normalized["growth_pct"]),
            batch_size=float(normalized["batch_size"]),
            missing_inputs=missing,
        )


def required_input_fields(mode: WorkloadMode) -> frozenset[str]:
    common = {
        "model_parameters_billion",
        "precision",
        "peak_multiplier",
        "region",
        "target_utilization_pct",
        "growth_pct",
    }
    mode_fields = {
        WorkloadMode.LLM_TRAINING: {"dataset_tb", "training_window_hours", "storage_tb"},
        WorkloadMode.LLM_INFERENCE: {
            "context_tokens",
            "input_tokens",
            "output_tokens",
            "requests_per_second",
            "concurrent_users",
            "latency_target_ms",
            "availability_target_pct",
        },
        WorkloadMode.RAG_INFERENCE: {
            "context_tokens",
            "input_tokens",
            "output_tokens",
            "requests_per_second",
            "concurrent_users",
            "latency_target_ms",
            "availability_target_pct",
            "dataset_tb",
            "storage_tb",
            "ingress_gb_per_day",
            "egress_gb_per_day",
        },
        WorkloadMode.VISION_INFERENCE: {
            "requests_per_second",
            "concurrent_users",
            "batch_size",
            "latency_target_ms",
            "availability_target_pct",
        },
        WorkloadMode.BATCH_AI_HPC: {
            "dataset_tb",
            "training_window_hours",
            "storage_tb",
            "ingress_gb_per_day",
            "egress_gb_per_day",
        },
    }
    return frozenset(common | mode_fields[mode])


def _normalize_aliases(raw: Mapping[str, Any]) -> dict[str, Any]:
    values = dict(raw)
    aliases = {
        "availability_target": "availability_target_pct",
        "average_input_tokens": "input_tokens",
        "average_output_tokens": "output_tokens",
        "concurrency": "concurrent_users",
        "target_utilization": "target_utilization_pct",
        "storage_growth": "storage_growth_pct",
        "growth": "growth_pct",
        "model_parameters": "model_parameters_billion",
        "model_parameters_billions": "model_parameters_billion",
        "peak_factor": "peak_multiplier",
    }
    for source, target in aliases.items():
        if target not in values and source in values:
            values[target] = values[source]

    overrides = values.get("assumption_overrides")
    if isinstance(overrides, Mapping):
        override_aliases = {"batch_size": "batch_size"}
        for source, target in override_aliases.items():
            if target not in values and source in overrides:
                values[target] = overrides[source]

    if "input_tokens" not in values and "output_tokens" not in values:
        tokens_per_request = values.get("tokens_per_request")
        if tokens_per_request is not None:
            total_tokens = _positive_number("tokens_per_request", tokens_per_request)
            values["input_tokens"] = total_tokens * 0.75
            values["output_tokens"] = total_tokens * 0.25

    traffic_aliases = {
        "ingress_gbps": "ingress_gb_per_day",
        "egress_gbps": "egress_gb_per_day",
    }
    for source, target in traffic_aliases.items():
        if target not in values and source in values:
            values[target] = _positive_number(source, values[source]) * 86_400 / 8
    return values


def _positive_number(name: str, raw: Any) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    zero_allowed = {
        "dataset_tb",
        "egress_gb_per_day",
        "egress_gbps",
        "growth_pct",
        "ingress_gb_per_day",
        "ingress_gbps",
        "input_tokens",
        "output_tokens",
        "storage_growth_pct",
        "storage_tb",
        "training_window_hours",
    }
    if value < 0 or (value == 0 and name not in zero_allowed):
        raise ValueError(f"{name} must be greater than zero")
    return value


def _is_missing_evidence(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _validate_bounded_percent(
    name: str, values: Mapping[str, float | str], minimum: float, maximum: float
) -> None:
    value = float(values[name])
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")


def _mapping(values: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    nested = values.get(key)
    if not isinstance(nested, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return nested
