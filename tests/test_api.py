from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def scenario_payload(
    name: str = "Realtime assistant",
    workload_mode: str = "llm_inference",
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Fictional regional workload",
        "workload_mode": workload_mode,
        "inputs": {
            "model_parameters_billions": 70,
            "model_family": "fictional-transformer-70b",
            "precision": "fp16",
            "context_tokens": 8_192,
            "tokens_per_request": 650,
            "average_input_tokens": 500,
            "average_output_tokens": 150,
            "tokens_per_day": 1_000_000,
            "requests_per_second": 18.5,
            "concurrency": 96,
            "peak_factor": 1.8,
            "latency_target_ms": 1_500,
            "availability_target_pct": 99.9,
            "dataset_tb": 10,
            "training_window_hours": 36,
            "storage_tb": 3.5,
            "storage_growth_pct": 15,
            "growth_pct": 25,
            "ingress_gbps": 2.0,
            "egress_gbps": 4.0,
            "region": "fictional-ap-southeast",
            "target_utilization_pct": 65,
            "assumption_overrides": {"batch_size": 8},
        },
    }


def deterministic_sizer(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "accelerator_count_range": {"low": 8, "high": 12},
        "bottleneck": "memory_bandwidth",
        "region": inputs["region"],
    }


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    with TestClient(
        create_app(
            database_path=tmp_path / "capacity.db",
            sizing_function=deterministic_sizer,
        )
    ) as test_client:
        yield test_client


def unwrap(response: Any, status_code: int = 200) -> Any:
    assert response.status_code == status_code, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    return payload["data"]


def test_health_and_scenario_crud(client: TestClient) -> None:
    assert unwrap(client.get("/health")) == {"status": "ok"}

    created = unwrap(client.post("/api/scenarios", json=scenario_payload()), 201)
    assert created["id"] == 1
    assert created["result"]["accelerator_count_range"] == {"low": 8, "high": 12}

    assert unwrap(client.get("/api/scenarios")) == [created]
    assert unwrap(client.get("/api/scenarios/1")) == created

    replacement = scenario_payload("Updated assistant")
    replacement["inputs"]["region"] = "fictional-us-central"  # type: ignore[index]
    updated = unwrap(client.put("/api/scenarios/1", json=replacement))
    assert updated["name"] == "Updated assistant"
    assert updated["result"]["region"] == "fictional-us-central"

    deleted = unwrap(client.delete("/api/scenarios/1"))
    assert deleted == {"id": 1, "deleted": True}
    assert unwrap(client.get("/api/scenarios")) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"derating_factor_pct": 50},
        {"monthly_hours": 730},
        {"power_rate_per_kwh": 0.14},
        {"batch_size": 0},
        {"batch_size": -4},
        {"batch_size": True},
    ],
)
def test_api_rejects_unsupported_or_invalid_assumption_overrides(
    client: TestClient,
    overrides: dict[str, object],
) -> None:
    payload = scenario_payload()
    payload["inputs"]["assumption_overrides"] = overrides  # type: ignore[index]

    response = client.post("/api/scenarios", json=payload)

    assert response.status_code == 422
    assert response.json()["success"] is False


@pytest.mark.parametrize(
    "workload_mode",
    [
        "llm_training",
        "llm_inference",
        "rag_inference",
        "vision_inference",
        "batch_ai_hpc",
    ],
)
def test_all_supported_workload_modes_are_accepted(
    client: TestClient,
    workload_mode: str,
) -> None:
    created = unwrap(
        client.post(
            "/api/scenarios",
            json=scenario_payload(f"Scenario {workload_mode}", workload_mode),
        ),
        201,
    )

    assert created["workload_mode"] == workload_mode


def test_compare_preserves_requested_order_and_rejects_missing_ids(client: TestClient) -> None:
    first = unwrap(client.post("/api/scenarios", json=scenario_payload("First")), 201)
    second = unwrap(client.post("/api/scenarios", json=scenario_payload("Second")), 201)

    comparison = unwrap(
        client.post(
            "/api/scenarios/compare",
            json={"scenario_ids": [second["id"], first["id"]]},
        )
    )
    assert [item["id"] for item in comparison["scenarios"]] == [second["id"], first["id"]]

    response = client.post(
        "/api/scenarios/compare",
        json={"scenario_ids": [first["id"], 999]},
    )
    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "scenario_not_found",
            "message": "Scenario 999 was not found.",
        },
    }


def test_json_and_markdown_exports_are_deterministic(client: TestClient) -> None:
    created = unwrap(client.post("/api/scenarios", json=scenario_payload()), 201)

    first_json = client.get(f"/api/scenarios/{created['id']}/export?format=json")
    second_json = client.get(f"/api/scenarios/{created['id']}/export?format=json")
    assert first_json.status_code == 200
    assert first_json.content == second_json.content
    assert first_json.headers["content-type"].startswith("application/json")
    assert json.loads(first_json.content)["name"] == "Realtime assistant"
    assert first_json.text.index('"description"') < first_json.text.index('"id"')

    first_markdown = client.get(f"/api/scenarios/{created['id']}/export?format=markdown")
    second_markdown = client.get(f"/api/scenarios/{created['id']}/export?format=markdown")
    assert first_markdown.content == second_markdown.content
    assert first_markdown.headers["content-type"].startswith("text/markdown")
    assert "# Capacity sizing: Realtime assistant" in first_markdown.text
    assert "## Inputs" in first_markdown.text
    assert "## Indicative result" in first_markdown.text
    assert "first-pass indicative range" in first_markdown.text.lower()
    assert "- **Planning status:** Unavailable" in first_markdown.text
    assert "- **Profile calibration:** `Unavailable`" in first_markdown.text
    assert "- **Evidence reference:** Unavailable" in first_markdown.text
    assert "- **Measurement scope:** Unavailable" in first_markdown.text
    assert "- **Profile limitations:** Unavailable" in first_markdown.text


def test_validation_and_not_found_errors_use_safe_envelopes(client: TestClient) -> None:
    blank = scenario_payload()
    blank["name"] = "   "
    response = client.post("/api/scenarios", json=blank)
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["details"]

    not_found = client.get("/api/scenarios/404")
    assert not_found.status_code == 404
    assert not_found.json()["error"] == {
        "code": "scenario_not_found",
        "message": "Scenario 404 was not found.",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("availability_target_pct", 100.1),
        ("target_utilization_pct", 0),
        ("peak_factor", 0.9),
        ("region", "   "),
    ],
)
def test_invalid_capacity_boundaries_are_rejected(
    client: TestClient,
    field: str,
    value: object,
) -> None:
    payload = scenario_payload()
    payload["inputs"][field] = value  # type: ignore[index]

    response = client.post("/api/scenarios", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_family", "   "),
        ("average_input_tokens", -1),
        ("average_output_tokens", -1),
        ("tokens_per_day", -1),
    ],
)
def test_explicit_model_and_token_volume_fields_are_validated(
    client: TestClient,
    field: str,
    value: object,
) -> None:
    payload = scenario_payload()
    payload["inputs"][field] = value  # type: ignore[index]

    response = client.post("/api/scenarios", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_zero_token_and_training_values_are_valid_non_applicable_inputs(
    client: TestClient,
) -> None:
    payload = scenario_payload()
    payload["inputs"].update(  # type: ignore[union-attr]
        {
            "average_input_tokens": 0,
            "average_output_tokens": 0,
            "tokens_per_day": 0,
            "training_window_hours": 0,
        }
    )

    created = unwrap(client.post("/api/scenarios", json=payload), 201)

    assert created["inputs"]["training_window_hours"] == 0


def test_engine_failures_are_redacted(tmp_path: Path) -> None:
    def unsafe_sizer(_inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("secret internal benchmark path")

    with TestClient(
        create_app(database_path=tmp_path / "capacity.db", sizing_function=unsafe_sizer),
        raise_server_exceptions=False,
    ) as client:
        response = client.post("/api/scenarios", json=scenario_payload())

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "internal_error",
            "message": "The capacity calculation could not be completed.",
        },
    }
    assert "secret" not in response.text


def test_create_runs_an_empty_but_valid_engine_result_once(tmp_path: Path) -> None:
    calls = 0

    def empty_sizer(_inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal calls
        calls += 1
        return {}

    with TestClient(
        create_app(database_path=tmp_path / "capacity.db", sizing_function=empty_sizer)
    ) as client:
        response = client.post("/api/scenarios", json=scenario_payload())

    assert response.status_code == 201
    assert response.json()["data"]["result"] == {}
    assert calls == 1


def test_unknown_routes_use_the_error_envelope(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {"code": "not_found", "message": "Route was not found."},
    }


def test_unknown_export_format_is_rejected(client: TestClient) -> None:
    created = unwrap(client.post("/api/scenarios", json=scenario_payload()), 201)
    response = client.get(f"/api/scenarios/{created['id']}/export?format=csv")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_fictional_demo_seed_is_explicit_and_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "seeded.db"

    for _ in range(2):
        with TestClient(
            create_app(
                database_path=database_path,
                sizing_function=deterministic_sizer,
                seed_demo_data=True,
            )
        ) as seeded_client:
            scenarios = unwrap(seeded_client.get("/api/scenarios"))

        assert len(scenarios) == 3
        assert {scenario["workload_mode"] for scenario in scenarios} == {
            "llm_training",
            "llm_inference",
            "rag_inference",
        }
        assert all("fictional" in scenario["description"].lower() for scenario in scenarios)
