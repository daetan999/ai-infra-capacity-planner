"""Fictional scenarios used to demonstrate the planner without customer data."""

from copy import deepcopy
from typing import Any


DEMO_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "name": "Fictional Atlas Pretraining Window",
        "description": (
            "Fictional research workload testing whether a fixed training window is feasible."
        ),
        "workload_mode": "llm_training",
        "inputs": {
            "model_family": "fictional dense transformer",
            "model_parameters_billions": 34,
            "precision": "bf16",
            "context_tokens": 4_096,
            "average_input_tokens": 3_200,
            "average_output_tokens": 0,
            "tokens_per_request": 3_200,
            "requests_per_second": 0.2,
            "tokens_per_day": 55_000_000,
            "concurrency": 8,
            "peak_factor": 1.2,
            "latency_target_ms": 60_000,
            "availability_target_pct": 99.0,
            "dataset_tb": 18,
            "training_window_hours": 168,
            "storage_tb": 72,
            "storage_growth_pct": 12,
            "ingress_gbps": 12,
            "egress_gbps": 3,
            "region": "fictional-ap-research",
            "target_utilization_pct": 78,
            "growth_pct": 20,
            "assumption_overrides": {
                "batch_size": 64,
                "quantization": "none",
                "profile": "illustrative-training-a",
            },
        },
    },
    {
        "name": "Fictional Meridian Realtime Assistant",
        "description": (
            "Fictional multilingual inference service with a latency-sensitive traffic peak."
        ),
        "workload_mode": "llm_inference",
        "inputs": {
            "model_family": "fictional instruction model",
            "model_parameters_billions": 70,
            "precision": "int8",
            "context_tokens": 8_192,
            "average_input_tokens": 540,
            "average_output_tokens": 310,
            "tokens_per_request": 850,
            "requests_per_second": 22,
            "tokens_per_day": 1_615_680_000,
            "concurrency": 140,
            "peak_factor": 2.1,
            "latency_target_ms": 1_300,
            "availability_target_pct": 99.9,
            "dataset_tb": 0.5,
            "training_window_hours": 0,
            "storage_tb": 5,
            "storage_growth_pct": 18,
            "ingress_gbps": 2.5,
            "egress_gbps": 8,
            "region": "fictional-ap-edge",
            "target_utilization_pct": 62,
            "growth_pct": 35,
            "assumption_overrides": {
                "batch_size": 8,
                "quantization": "int8",
                "profile": "illustrative-inference-b",
            },
        },
    },
    {
        "name": "Fictional Northstar Knowledge Retrieval",
        "description": (
            "Fictional RAG workload sizing retrieval growth and generation capacity together."
        ),
        "workload_mode": "rag_inference",
        "inputs": {
            "model_family": "fictional retrieval generator",
            "model_parameters_billions": 13,
            "precision": "fp16",
            "context_tokens": 16_384,
            "average_input_tokens": 2_400,
            "average_output_tokens": 420,
            "tokens_per_request": 2_820,
            "requests_per_second": 9,
            "tokens_per_day": 730_944_000,
            "concurrency": 72,
            "peak_factor": 1.7,
            "latency_target_ms": 2_200,
            "availability_target_pct": 99.95,
            "dataset_tb": 28,
            "training_window_hours": 0,
            "storage_tb": 54,
            "storage_growth_pct": 45,
            "ingress_gbps": 4,
            "egress_gbps": 5,
            "region": "fictional-eu-core",
            "target_utilization_pct": 58,
            "growth_pct": 40,
            "assumption_overrides": {
                "batch_size": 4,
                "quantization": "none",
                "profile": "illustrative-balanced-c",
            },
        },
    },
)


def fresh_demo_scenarios() -> list[dict[str, Any]]:
    """Return isolated copies so callers never mutate the canonical fixtures."""

    return deepcopy(list(DEMO_SCENARIOS))
