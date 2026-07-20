"""Vendor-neutral, deterministic first-pass capacity sizing.

The formulas in this module produce indicative planning ranges. They deliberately use
normalized workload units and illustrative profiles; they are not benchmark results or quotes.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from app.domain import AcceleratorProfile, SizingInputs, WorkloadMode

DEFAULT_PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "accelerator_profiles.yaml"


def load_accelerator_profiles(
    profiles_path: str | Path | None = None,
) -> dict[str, AcceleratorProfile]:
    """Load and validate illustrative accelerator profiles."""
    path = Path(profiles_path) if profiles_path is not None else DEFAULT_PROFILES_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to load accelerator profiles from {path}") from exc
    if not isinstance(raw, Mapping) or not isinstance(raw.get("profiles"), Mapping):
        raise ValueError("Accelerator profile YAML must contain a profiles mapping")
    return {
        str(profile_id): AcceleratorProfile.from_mapping(str(profile_id), values)
        for profile_id, values in raw["profiles"].items()
        if isinstance(values, Mapping)
    }


def calculate_capacity(
    inputs: Mapping[str, Any], *, profiles_path: str | Path | None = None
) -> dict[str, Any]:
    """Return a deterministic, JSON-serializable indicative sizing result.

    ``workload_mode`` is the canonical mode input. ``mode`` remains accepted for simple clients.
    No network calls, live prices, or vendor performance claims are used.
    """
    sizing = SizingInputs.from_mapping(inputs)
    profiles = load_accelerator_profiles(profiles_path)
    try:
        profile = profiles[sizing.accelerator_profile]
    except KeyError as exc:
        available = ", ".join(sorted(profiles))
        raise ValueError(
            f"Unknown accelerator profile: {sizing.accelerator_profile!r}. "
            f"Choose one of: {available}"
        ) from exc

    confidence = _confidence(sizing)
    estimate = _estimate(sizing, profile, confidence["score"])
    capacity = _capacity_dimensions(sizing, profile, estimate)
    return {
        "mode": sizing.mode.value,
        "profile": profile.public_dict(),
        "capacity": capacity,
        "views": _views(sizing, profile, estimate),
        "bottleneck": _bottleneck(sizing, estimate),
        "confidence": confidence,
        "benchmark_assumptions": _benchmark_assumptions(sizing, profile),
        "validation_questions": _validation_questions(sizing),
        "poc_plan": _poc_plan(sizing),
        "commercial_band": _commercial_band(capacity["monthly_cost_usd"]),
        "sensitivities": _sensitivities(sizing, profile, confidence["score"]),
        "guardrail": (
            "Indicative first-pass range only; validate with representative measurements "
            "before architecture or commercial commitment."
        ),
    }


def _normalized_demand(sizing: SizingInputs) -> float:
    parameter_scale = math.sqrt(max(sizing.model_parameters_billion, 1) / 7)
    latency_factor = max(1.0, (1_500 / sizing.latency_target_ms) ** 0.35)
    concurrency_factor = 1 + min(sizing.concurrent_users / 1_000, 1.5)
    precision_factor = sizing.precision.work_factor

    if sizing.mode is WorkloadMode.LLM_TRAINING:
        return (
            sizing.model_parameters_billion
            * sizing.dataset_tb
            * 100
            / sizing.training_window_hours
            * sizing.peak_multiplier
            * precision_factor
        )
    if sizing.mode in {WorkloadMode.LLM_INFERENCE, WorkloadMode.RAG_INFERENCE}:
        token_factor = (sizing.input_tokens + sizing.output_tokens) / 1_000
        context_factor = math.sqrt(max(sizing.context_tokens, 1) / 4_096)
        demand = (
            sizing.requests_per_second
            * token_factor
            * parameter_scale
            * context_factor
            * concurrency_factor
            * sizing.peak_multiplier
            * latency_factor
            * precision_factor
        )
        if sizing.mode is WorkloadMode.RAG_INFERENCE:
            retrieval_factor = 1.18 + min(sizing.dataset_tb / 100, 0.35)
            return demand * retrieval_factor
        return demand
    if sizing.mode is WorkloadMode.VISION_INFERENCE:
        batch_efficiency = min(1 + math.log2(max(sizing.batch_size, 1)) * 0.12, 1.5)
        return (
            sizing.requests_per_second
            * 5
            * concurrency_factor
            * sizing.peak_multiplier
            * latency_factor
            / batch_efficiency
        )
    return (
        sizing.dataset_tb
        * 1_024
        / sizing.training_window_hours
        * sizing.peak_multiplier
        * precision_factor
        * 10
    )


def _memory_floor(sizing: SizingInputs, profile: AcceleratorProfile) -> int:
    if sizing.mode is WorkloadMode.LLM_TRAINING:
        working_set_gb = (
            sizing.model_parameters_billion * sizing.precision.bytes_per_parameter * 7.5
        )
    elif sizing.mode in {WorkloadMode.LLM_INFERENCE, WorkloadMode.RAG_INFERENCE}:
        working_set_gb = (
            sizing.model_parameters_billion * sizing.precision.bytes_per_parameter * 1.2
        )
    else:
        working_set_gb = profile.memory_gb * 0.5
    return max(1, math.ceil(working_set_gb / (profile.memory_gb * 0.9)))


def _estimate(
    sizing: SizingInputs,
    profile: AcceleratorProfile,
    confidence_score: int,
    *,
    demand_multiplier: float = 1.0,
) -> dict[str, int | float]:
    demand = _normalized_demand(sizing) * demand_multiplier
    throughput = profile.theoretical_throughput[sizing.mode.value]
    theoretical = max(1, math.ceil(demand / throughput))
    throughput_floor = max(1, math.ceil(demand / (throughput * profile.derating_factor)))
    memory_floor = _memory_floor(sizing, profile)
    constraint_floor = max(throughput_floor, memory_floor)
    utilized = math.ceil(constraint_floor / (sizing.target_utilization_pct / 100))
    availability_factor = 1.0
    if sizing.availability_target_pct >= 99.99:
        availability_factor = 1.3
    elif sizing.availability_target_pct >= 99.9:
        availability_factor = 1.15
    protected = math.ceil(utilized * availability_factor)
    recommended_min = max(1, math.ceil(protected * (1 + sizing.growth_pct / 100)))
    uncertainty = 1.12 + (100 - confidence_score) / 250
    recommended_max = max(recommended_min, math.ceil(recommended_min * uncertainty))
    return {
        "demand": round(demand, 4),
        "theoretical": theoretical,
        "throughput_floor": throughput_floor,
        "memory_floor": memory_floor,
        "derated": max(throughput_floor, memory_floor),
        "recommended_min": recommended_min,
        "recommended_max": recommended_max,
    }


def _capacity_dimensions(
    sizing: SizingInputs,
    profile: AcceleratorProfile,
    estimate: Mapping[str, int | float],
) -> dict[str, dict[str, int | float | str]]:
    accelerator_min = int(estimate["recommended_min"])
    accelerator_max = int(estimate["recommended_max"])
    cpu_per_accelerator = {
        WorkloadMode.LLM_TRAINING: 20,
        WorkloadMode.LLM_INFERENCE: 16,
        WorkloadMode.RAG_INFERENCE: 20,
        WorkloadMode.VISION_INFERENCE: 12,
        WorkloadMode.BATCH_AI_HPC: 24,
    }[sizing.mode]
    memory_per_accelerator = {
        WorkloadMode.LLM_TRAINING: 192,
        WorkloadMode.LLM_INFERENCE: 96,
        WorkloadMode.RAG_INFERENCE: 128,
        WorkloadMode.VISION_INFERENCE: 64,
        WorkloadMode.BATCH_AI_HPC: 160,
    }[sizing.mode]
    storage_base = _storage_base(sizing)
    storage_min = storage_base * (1 + sizing.storage_growth_pct / 100)
    storage_max = storage_min * (1 + sizing.growth_pct / 100) * 1.2
    storage_throughput_min, storage_throughput_max = _storage_throughput_range(
        sizing,
        accelerator_min,
        accelerator_max,
    )
    io_gbps = max(sizing.ingress_gb_per_day, sizing.egress_gb_per_day) * 8 / 86_400
    fabric_gbps = accelerator_min * (
        0.5 if sizing.mode is WorkloadMode.LLM_TRAINING else 0.12
    )
    network_min = max(0.1, io_gbps * sizing.peak_multiplier, fabric_gbps)
    network_max = max(network_min, network_min * 1.5, accelerator_max * 0.18)
    rack_min = max(1, math.ceil(accelerator_min / 8))
    rack_max = max(rack_min, math.ceil(accelerator_max / 6))
    power_min = accelerator_min * profile.power_watts_min / 1_000 * 1.25
    power_max = accelerator_max * profile.power_watts_max / 1_000 * 1.4
    cpu_min = accelerator_min * cpu_per_accelerator
    cpu_max = math.ceil(accelerator_max * cpu_per_accelerator * 1.15)
    memory_min = accelerator_min * memory_per_accelerator
    memory_max = math.ceil(accelerator_max * memory_per_accelerator * 1.15)
    cost_min = (
        accelerator_min * profile.monthly_price_usd_min
        + cpu_min * 25
        + storage_min * 30
        + network_min * 400
    )
    cost_max = (
        accelerator_max * profile.monthly_price_usd_max
        + cpu_max * 35
        + storage_max * 45
        + network_max * 650
    )
    return {
        "accelerators": _range(accelerator_min, accelerator_max, "devices", integer=True),
        "cpu_cores": _range(cpu_min, cpu_max, "vCPU", integer=True),
        "memory_gb": _range(memory_min, memory_max, "GB", integer=True),
        "storage_tb": _range(storage_min, storage_max, "TB"),
        "storage_throughput_gbps": _range(
            storage_throughput_min,
            storage_throughput_max,
            "Gbps",
        ),
        "network_gbps": _range(network_min, network_max, "Gbps"),
        "racks": _range(rack_min, rack_max, "racks", integer=True),
        "power_kw": _range(power_min, power_max, "kW"),
        "monthly_cost_usd": _range(cost_min, cost_max, "USD/month", integer=True),
    }


def _storage_base(sizing: SizingInputs) -> float:
    if sizing.mode is WorkloadMode.LLM_TRAINING:
        return max(sizing.storage_tb, sizing.dataset_tb * 2.5)
    if sizing.mode is WorkloadMode.RAG_INFERENCE:
        return max(sizing.storage_tb, sizing.dataset_tb * 1.35)
    if sizing.mode is WorkloadMode.BATCH_AI_HPC:
        return max(sizing.storage_tb, sizing.dataset_tb * 2)
    return max(sizing.storage_tb, sizing.dataset_tb * 1.1)


def _storage_throughput_range(
    sizing: SizingInputs,
    accelerator_min: int,
    accelerator_max: int,
) -> tuple[float, float]:
    """Estimate the sustained storage path needed to keep the modeled fleet fed."""

    window_seconds = max(sizing.training_window_hours * 3_600, 3_600)
    dataset_scan_gbps = sizing.dataset_tb * 8_000 / window_seconds
    transfer_gbps = max(sizing.ingress_gb_per_day, sizing.egress_gb_per_day) * 8 / 86_400
    mode_factor = {
        WorkloadMode.LLM_TRAINING: 3.0,
        WorkloadMode.LLM_INFERENCE: 0.5,
        WorkloadMode.RAG_INFERENCE: 1.6,
        WorkloadMode.VISION_INFERENCE: 0.8,
        WorkloadMode.BATCH_AI_HPC: 2.0,
    }[sizing.mode]
    minimum = max(
        0.05,
        dataset_scan_gbps * mode_factor,
        transfer_gbps * sizing.peak_multiplier,
        accelerator_min * 0.03,
    )
    maximum = max(minimum, minimum * 1.8, accelerator_max * 0.06)
    return minimum, maximum


def _views(
    sizing: SizingInputs,
    profile: AcceleratorProfile,
    estimate: Mapping[str, int | float],
) -> dict[str, int | float]:
    return {
        "normalized_demand_units_per_second": estimate["demand"],
        "theoretical_accelerators": estimate["theoretical"],
        "throughput_floor_accelerators": estimate["throughput_floor"],
        "memory_floor_accelerators": estimate["memory_floor"],
        "derated_accelerators": estimate["derated"],
        "profile_derating_pct": round(profile.derating_factor * 100, 2),
        "target_utilization_pct": sizing.target_utilization_pct,
        "peak_multiplier": sizing.peak_multiplier,
    }


def _bottleneck(
    sizing: SizingInputs, estimate: Mapping[str, int | float]
) -> dict[str, str]:
    if estimate["memory_floor"] > estimate["throughput_floor"]:
        return {
            "primary": "accelerator_memory",
            "reason": "The modeled working set needs more devices than normalized throughput.",
        }
    io_gbps = max(sizing.ingress_gb_per_day, sizing.egress_gb_per_day) * 8 / 86_400
    if io_gbps * sizing.peak_multiplier > int(estimate["recommended_min"]) * 0.5:
        return {
            "primary": "network_ingress_egress",
            "reason": (
                "Daily data movement and peak factor dominate the indicative fabric allowance."
            ),
        }
    if sizing.storage_growth_pct >= 75:
        return {
            "primary": "storage_capacity",
            "reason": "Storage growth is the largest explicit planning pressure.",
        }
    return {
        "primary": "compute_throughput",
        "reason": "Normalized peak demand after derating sets the largest capacity floor.",
    }


def _confidence(sizing: SizingInputs) -> dict[str, Any]:
    score = max(20, 100 - len(sizing.missing_inputs) * 7)
    level = "high" if score >= 80 else "medium" if score >= 55 else "low"
    return {
        "level": level,
        "score": score,
        "missing_inputs": list(sizing.missing_inputs),
        "basis": (
            "Completeness score only; confidence must be raised with workload-specific benchmarks."
        ),
    }


def _benchmark_assumptions(
    sizing: SizingInputs, profile: AcceleratorProfile
) -> list[dict[str, str | float]]:
    assumptions: list[dict[str, str | float]] = [
        {
            "name": "Profile theoretical throughput",
            "value": profile.theoretical_throughput[sizing.mode.value],
            "source_type": "illustrative normalized profile",
            "caveat": "Not a measured or vendor-published benchmark.",
        },
        {
            "name": "Planning derating",
            "value": profile.derating_factor,
            "source_type": "illustrative planning factor",
            "caveat": "Replace after representative benchmark runs.",
        },
        {
            "name": "Monthly device price",
            "value": f"{profile.monthly_price_usd_min:g}-{profile.monthly_price_usd_max:g} USD",
            "source_type": profile.price_source_type,
            "caveat": "Not a quote; excludes contract, region, and service-specific adjustments.",
        },
        {
            "name": "Demand model",
            "value": "deterministic normalized workload units",
            "source_type": "planner heuristic",
            "caveat": "Calibrate with observed latency, throughput, memory, and utilization.",
        },
    ]
    if sizing.missing_inputs:
        assumptions.append(
            {
                "name": "Defaulted planning inputs",
                "value": ", ".join(sizing.missing_inputs),
                "source_type": "measurement required",
                "caveat": "Defaults preserve a first-pass range but reduce confidence.",
            }
        )
    return assumptions


def _validation_questions(sizing: SizingInputs) -> list[str]:
    prompts = {
        "model_parameters_billion": "What model size and architecture will be tested?",
        "precision": "Which precision or quantization policy meets the quality threshold?",
        "context_tokens": "What are the p50 and p95 context lengths?",
        "input_tokens": "What is the observed input-token distribution?",
        "output_tokens": "What is the observed output-token distribution?",
        "requests_per_second": "What are sustained and burst request rates?",
        "concurrent_users": "What concurrency appears at the peak business window?",
        "latency_target_ms": "Which p50 and p95 latency targets are contractual?",
        "availability_target_pct": "What availability objective and failure-domain policy apply?",
        "dataset_tb": "What is the usable dataset size after filtering and replication?",
        "training_window_hours": "What completion or batch window is required?",
        "storage_tb": "How much hot, warm, and retained storage is required?",
        "ingress_gb_per_day": "What sustained and peak ingress volume is measured?",
        "egress_gb_per_day": "What sustained and peak egress volume is measured?",
        "target_utilization_pct": "What utilization headroom is operationally acceptable?",
        "peak_multiplier": "What peak-to-average demand ratio appears in telemetry?",
        "growth_pct": "What planning-horizon demand growth should be funded?",
        "region": "Which fictional planning region constraints should be modeled?",
        "batch_size": "Which batch sizes preserve latency and quality?",
    }
    questions = [prompts[field] for field in sizing.missing_inputs if field in prompts]
    questions.extend(
        [
            "Which representative benchmark corpus and traffic replay will approve the design?",
            "Which failure-domain, observability, and rollback tests must the PoC pass?",
        ]
    )
    return questions


def _poc_plan(sizing: SizingInputs) -> dict[str, Any]:
    mode_measurements = {
        WorkloadMode.LLM_TRAINING: [
            "step time and end-to-end completion window",
            "accelerator memory high-water mark",
            "compute, fabric, and checkpoint utilization",
        ],
        WorkloadMode.LLM_INFERENCE: [
            "time to first token and p95 end-to-end latency",
            "tokens per second at representative concurrency",
            "accelerator memory and utilization",
        ],
        WorkloadMode.RAG_INFERENCE: [
            "retrieval and generation latency split",
            "retrieval recall on a representative corpus",
            "tokens per second, memory, cache, and index utilization",
        ],
        WorkloadMode.VISION_INFERENCE: [
            "p95 latency and images per second by batch size",
            "preprocessing, accelerator, and postprocessing utilization",
            "quality metric under chosen precision",
        ],
        WorkloadMode.BATCH_AI_HPC: [
            "records processed per hour and completion window",
            "compute, memory, storage, and network utilization",
            "checkpoint, retry, and recovery time",
        ],
    }
    return {
        "objective": (
            "Validate this first-pass range with representative traffic replay and measured "
            f"{sizing.mode.value.replace('_', ' ')} behavior."
        ),
        "measurements": mode_measurements[sizing.mode],
        "acceptance_criteria": [
            "Meet agreed p95 service or completion target at modeled peak",
            "Stay within agreed utilization and memory headroom",
            "Reconcile measured unit economics with the indicative commercial band",
        ],
    }


def _commercial_band(monthly_cost: Mapping[str, int | float | str]) -> dict[str, Any]:
    midpoint = (float(monthly_cost["min"]) + float(monthly_cost["max"])) / 2
    if midpoint < 10_000:
        label = "exploration"
    elif midpoint < 50_000:
        label = "departmental"
    elif midpoint < 250_000:
        label = "enterprise"
    else:
        label = "strategic"
    return {
        "label": label,
        "monthly_range_usd": dict(monthly_cost),
        "caveat": "Illustrative planning band, not a vendor quote or committed price.",
    }


def _sensitivities(
    sizing: SizingInputs, profile: AcceleratorProfile, confidence_score: int
) -> dict[str, dict[str, Any]]:
    batching = _estimate(sizing, profile, confidence_score, demand_multiplier=0.85)
    quantized = _estimate(
        replace(sizing, precision=sizing.precision.next_lower), profile, confidence_score
    )
    growth = _estimate(
        replace(sizing, growth_pct=sizing.growth_pct + 20), profile, confidence_score
    )
    latency = _estimate(
        replace(sizing, latency_target_ms=sizing.latency_target_ms * 0.75),
        profile,
        confidence_score,
    )
    return {
        "batching": {
            "change": "tuned representative batching",
            "assumption": "illustrative 15% throughput uplift",
            "accelerators": _accelerator_range(batching),
        },
        "quantization": {
            "change": f"{sizing.precision.value} to {sizing.precision.next_lower.value}",
            "assumption": "next lower precision with illustrative efficiency factors",
            "accelerators": _accelerator_range(quantized),
        },
        "growth": {
            "change": "+20 percentage points",
            "assumption": "same workload shape and service targets",
            "accelerators": _accelerator_range(growth),
        },
        "latency": {
            "change": "25% tighter target",
            "assumption": "same traffic, model, precision, and batching",
            "accelerators": _accelerator_range(latency),
        },
    }


def _accelerator_range(estimate: Mapping[str, int | float]) -> dict[str, int]:
    return {
        "min": int(estimate["recommended_min"]),
        "max": int(estimate["recommended_max"]),
    }


def _range(
    minimum: int | float, maximum: int | float, unit: str, *, integer: bool = False
) -> dict[str, int | float | str]:
    if integer:
        return {"min": math.ceil(minimum), "max": math.ceil(maximum), "unit": unit}
    return {"min": round(float(minimum), 2), "max": round(float(maximum), 2), "unit": unit}
