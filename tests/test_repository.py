from __future__ import annotations

from pathlib import Path

import pytest

from app.repository import ScenarioNotFoundError, ScenarioRepository


def scenario_payload(name: str = "Realtime assistant") -> dict[str, object]:
    return {
        "name": name,
        "description": "Fictional regional support workload",
        "workload_mode": "llm_inference",
        "inputs": {
            "model_parameters_billions": 70,
            "precision": "fp16",
            "context_tokens": 8_192,
            "tokens_per_request": 650,
            "requests_per_second": 18.5,
            "concurrency": 96,
            "peak_factor": 1.8,
            "latency_target_ms": 1_500,
            "availability_target_pct": 99.9,
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


@pytest.fixture
def repository(tmp_path: Path) -> ScenarioRepository:
    return ScenarioRepository(tmp_path / "capacity.db")


def test_repository_crud_round_trip(repository: ScenarioRepository) -> None:
    created = repository.create(scenario_payload())

    assert created.id == 1
    assert created.name == "Realtime assistant"
    assert created.inputs["context_tokens"] == 8_192
    assert repository.get(created.id) == created
    assert repository.list() == [created]

    updated = repository.update(
        created.id,
        {**scenario_payload("Peak assistant"), "description": "Updated synthetic peak"},
    )

    assert updated.id == created.id
    assert updated.name == "Peak assistant"
    assert updated.description == "Updated synthetic peak"
    assert updated.created_at == created.created_at
    assert updated.updated_at >= created.updated_at
    assert repository.list() == [updated]

    repository.delete(created.id)
    assert repository.list() == []


def test_repository_raises_typed_not_found_errors(repository: ScenarioRepository) -> None:
    for operation in (
        lambda: repository.get(404),
        lambda: repository.update(404, scenario_payload()),
        lambda: repository.delete(404),
    ):
        with pytest.raises(ScenarioNotFoundError, match="404"):
            operation()


def test_repository_instances_share_persisted_state(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "capacity.db"
    first = ScenarioRepository(database_path)
    created = first.create(scenario_payload("Persisted scenario"))

    second = ScenarioRepository(database_path)

    assert second.get(created.id).name == "Persisted scenario"
