from __future__ import annotations

from copy import deepcopy

import pytest

from app.domain import WorkloadMode
from app.engine import calculate_capacity, load_accelerator_profiles

BASE_INPUTS = {
    "mode": "llm_inference",
    "accelerator_profile": "illustrative-balanced",
    "model_parameters_billion": 70,
    "precision": "fp16",
    "context_tokens": 8_192,
    "input_tokens": 1_200,
    "output_tokens": 300,
    "requests_per_second": 24,
    "concurrent_users": 180,
    "peak_multiplier": 1.8,
    "latency_target_ms": 800,
    "availability_target_pct": 99.9,
    "dataset_tb": 4,
    "training_window_hours": 168,
    "storage_tb": 12,
    "storage_growth_pct": 20,
    "ingress_gb_per_day": 320,
    "egress_gb_per_day": 460,
    "region": "fictional-region-1",
    "target_utilization_pct": 70,
    "growth_pct": 25,
    "batch_size": 8,
}


def test_profiles_are_vendor_neutral_and_explicitly_illustrative() -> None:
    profiles = load_accelerator_profiles()

    assert len(profiles) >= 3
    for profile_id, profile in profiles.items():
        assert profile_id.startswith("illustrative-")
        assert profile.illustrative is True
        assert profile.memory_gb > 0
        assert set(profile.theoretical_throughput) == {mode.value for mode in WorkloadMode}
        assert all(value > 0 for value in profile.theoretical_throughput.values())
        assert 0 < profile.derating_factor < 1
        assert 0 < profile.power_watts_min <= profile.power_watts_max
        assert profile.monthly_price_usd_min <= profile.monthly_price_usd_max
        assert profile.price_source_type == "illustrative planning placeholder"


def test_calculation_is_deterministic_and_json_friendly() -> None:
    first = calculate_capacity(deepcopy(BASE_INPUTS))
    second = calculate_capacity(deepcopy(BASE_INPUTS))

    assert first == second
    assert first["mode"] == "llm_inference"
    assert first["profile"]["id"] == "illustrative-balanced"
    assert first["profile"]["illustrative"] is True
    assert isinstance(first["benchmark_assumptions"], list)
    assert isinstance(first["validation_questions"], list)


def test_api_alias_mapping_matches_canonical_engine_inputs() -> None:
    api_inputs = {
        "workload_mode": BASE_INPUTS["mode"],
        "model_parameters_billions": BASE_INPUTS["model_parameters_billion"],
        "average_input_tokens": BASE_INPUTS["input_tokens"],
        "average_output_tokens": BASE_INPUTS["output_tokens"],
        "context_tokens": BASE_INPUTS["context_tokens"],
        "requests_per_second": BASE_INPUTS["requests_per_second"],
        "concurrency": BASE_INPUTS["concurrent_users"],
        "peak_factor": BASE_INPUTS["peak_multiplier"],
        "latency_target_ms": BASE_INPUTS["latency_target_ms"],
        "availability_target_pct": BASE_INPUTS["availability_target_pct"],
        "dataset_tb": BASE_INPUTS["dataset_tb"],
        "training_window_hours": BASE_INPUTS["training_window_hours"],
        "storage_tb": BASE_INPUTS["storage_tb"],
        "storage_growth_pct": BASE_INPUTS["storage_growth_pct"],
        "ingress_gbps": BASE_INPUTS["ingress_gb_per_day"] * 8 / 86_400,
        "egress_gbps": BASE_INPUTS["egress_gb_per_day"] * 8 / 86_400,
        "region": BASE_INPUTS["region"],
        "target_utilization_pct": BASE_INPUTS["target_utilization_pct"],
        "growth_pct": BASE_INPUTS["growth_pct"],
        "assumption_overrides": {
            "accelerator_profile": BASE_INPUTS["accelerator_profile"],
            "batch_size": BASE_INPUTS["batch_size"],
            "quantization": BASE_INPUTS["precision"],
        },
    }

    assert calculate_capacity(api_inputs) == calculate_capacity(BASE_INPUTS)


@pytest.mark.parametrize("mode", [mode.value for mode in WorkloadMode])
def test_every_workload_mode_returns_complete_indicative_ranges(mode: str) -> None:
    result = calculate_capacity({**BASE_INPUTS, "mode": mode})
    capacity = result["capacity"]

    for dimension in (
        "accelerators",
        "cpu_cores",
        "memory_gb",
        "storage_tb",
        "network_gbps",
        "racks",
        "power_kw",
        "monthly_cost_usd",
    ):
        assert set(capacity[dimension]) >= {"min", "max", "unit"}
        assert capacity[dimension]["min"] > 0
        assert capacity[dimension]["max"] >= capacity[dimension]["min"]

    assert result["bottleneck"]["primary"] in {
        "accelerator_memory",
        "compute_throughput",
        "network_ingress_egress",
        "storage_capacity",
    }
    assert result["confidence"]["level"] in {"low", "medium", "high"}
    assert 0 <= result["confidence"]["score"] <= 100
    assert result["commercial_band"]["monthly_range_usd"] == capacity[
        "monthly_cost_usd"
    ]
    assert result["poc_plan"]["measurements"]


def test_views_show_theoretical_derated_and_utilization_capacity() -> None:
    result = calculate_capacity(BASE_INPUTS)
    views = result["views"]
    accelerators = result["capacity"]["accelerators"]

    assert views["theoretical_accelerators"] <= views["derated_accelerators"]
    assert views["derated_accelerators"] <= accelerators["min"]
    assert accelerators["max"] >= accelerators["min"]
    assert views["profile_derating_pct"] == pytest.approx(62.0)
    assert views["target_utilization_pct"] == 70
    assert views["peak_multiplier"] == 1.8


def test_growth_and_latency_sensitivities_never_understate_baseline() -> None:
    result = calculate_capacity(BASE_INPUTS)
    baseline = result["capacity"]["accelerators"]["min"]
    sensitivities = result["sensitivities"]

    assert sensitivities["growth"]["accelerators"]["min"] >= baseline
    assert sensitivities["latency"]["accelerators"]["min"] >= baseline
    assert sensitivities["growth"]["change"] == "+20 percentage points"
    assert sensitivities["latency"]["change"] == "25% tighter target"


def test_batching_and_quantization_sensitivities_show_efficiency_opportunity() -> None:
    result = calculate_capacity(BASE_INPUTS)
    baseline = result["capacity"]["accelerators"]["min"]
    sensitivities = result["sensitivities"]

    assert sensitivities["batching"]["accelerators"]["min"] <= baseline
    assert sensitivities["quantization"]["accelerators"]["min"] <= baseline
    assert sensitivities["batching"]["assumption"] == "illustrative 15% throughput uplift"
    assert sensitivities["quantization"]["assumption"] == (
        "next lower precision with illustrative efficiency factors"
    )


def test_sparse_inputs_lower_confidence_and_generate_validation_work() -> None:
    result = calculate_capacity(
        {
            "mode": "rag_inference",
            "accelerator_profile": "illustrative-balanced",
            "requests_per_second": 12,
        }
    )

    assert result["confidence"]["level"] == "low"
    assert result["confidence"]["missing_inputs"]
    assert "model_parameters_billion" in result["confidence"]["missing_inputs"]
    assert len(result["validation_questions"]) >= 3
    assert "representative traffic replay" in result["poc_plan"]["objective"].lower()
    assert any(
        item["source_type"] == "measurement required"
        for item in result["benchmark_assumptions"]
    )


def test_memory_floor_can_become_primary_bottleneck() -> None:
    result = calculate_capacity(
        {
            **BASE_INPUTS,
            "mode": "llm_training",
            "model_parameters_billion": 700,
            "dataset_tb": 0.1,
            "training_window_hours": 720,
            "precision": "fp32",
        }
    )

    assert result["bottleneck"]["primary"] == "accelerator_memory"
    assert result["views"]["memory_floor_accelerators"] > result["views"][
        "throughput_floor_accelerators"
    ]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"mode": "unsupported"}, "Unsupported workload mode"),
        ({"accelerator_profile": "real-vendor"}, "Unknown accelerator profile"),
        ({"requests_per_second": -1}, "requests_per_second must be greater than zero"),
        ({"precision": "binary"}, "Unsupported precision"),
    ],
)
def test_invalid_inputs_fail_with_actionable_messages(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        calculate_capacity({**BASE_INPUTS, **overrides})


def test_non_applicable_api_fields_may_be_zero() -> None:
    result = calculate_capacity(
        {
            "workload_mode": "llm_inference",
            "model_parameters_billions": 13,
            "average_input_tokens": 500,
            "average_output_tokens": 0,
            "requests_per_second": 4,
            "concurrency": 20,
            "peak_factor": 1.2,
            "training_window_hours": 0,
            "dataset_tb": 0,
            "storage_tb": 0,
            "ingress_gbps": 0,
            "egress_gbps": 0,
        }
    )

    assert result["capacity"]["accelerators"]["min"] > 0


def test_training_requires_a_nonzero_completion_window() -> None:
    with pytest.raises(ValueError, match="training_window_hours must be greater than zero"):
        calculate_capacity(
            {
                **BASE_INPUTS,
                "workload_mode": "llm_training",
                "training_window_hours": 0,
            }
        )
