from pathlib import Path

from fastapi.testclient import TestClient

from app.engine import calculate_capacity
from app.main import create_app


def test_scenario_flows_from_validated_input_to_report(tmp_path: Path) -> None:
    payload = {
        "name": "Fictional integration assistant",
        "description": "Fictional end-to-end verification scenario",
        "workload_mode": "llm_inference",
        "inputs": {
            "model_family": "fictional instruction model",
            "model_parameters_billions": 34,
            "precision": "int8",
            "context_tokens": 8_192,
            "average_input_tokens": 600,
            "average_output_tokens": 250,
            "tokens_per_request": 850,
            "tokens_per_day": 367_200_000,
            "requests_per_second": 12,
            "concurrency": 80,
            "peak_factor": 1.8,
            "latency_target_ms": 1_500,
            "availability_target_pct": 99.9,
            "storage_tb": 4,
            "storage_growth_pct": 20,
            "growth_pct": 30,
            "ingress_gbps": 2,
            "egress_gbps": 4,
            "region": "fictional-integration-region",
            "target_utilization_pct": 65,
            "accelerator_profile": "illustrative-balanced",
            "assumption_overrides": {"batch_size": 8},
        },
    }

    with TestClient(
        create_app(
            database_path=tmp_path / "planner.db",
            sizing_function=calculate_capacity,
        )
    ) as client:
        response = client.post("/api/scenarios", json=payload)
        assert response.status_code == 201, response.text
        scenario = response.json()["data"]

        result = scenario["result"]
        assert result["mode"] == "llm_inference"
        assert result["profile"]["illustrative"] is True
        assert result["profile"]["calibration_status"] == "illustrative"
        assert result["planning_status"].startswith("Planning status: illustrative")
        assert result["capacity"]["accelerators"]["min"] > 0
        assert result["capacity"]["monthly_cost_usd"]["max"] > 0
        assert 0 <= result["confidence"]["score"] <= 100
        assert result["benchmark_assumptions"]
        assert result["validation_questions"]
        assert result["poc_plan"]["measurements"]
        assert result["commercial_band"]["monthly_range_usd"] == result["capacity"][
            "monthly_cost_usd"
        ]

        report = client.get(f"/api/scenarios/{scenario['id']}/export?format=markdown")
        assert report.status_code == 200
        assert "Fictional integration assistant" in report.text
        assert "first-pass indicative range" in report.text.lower()
        assert "Planning status: illustrative" in report.text
        assert '"calibration_status": "illustrative"' in report.text
        assert "Internal normalized planning model" in report.text
        assert "Generic workload-unit planning" in report.text
        assert "Not comparable to vendor throughput" in report.text
