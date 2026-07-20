from app.demo_data import DEMO_SCENARIOS


def test_demo_scenarios_cover_required_fictional_workloads() -> None:
    assert len(DEMO_SCENARIOS) == 3
    assert {scenario["workload_mode"] for scenario in DEMO_SCENARIOS} == {
        "llm_training",
        "llm_inference",
        "rag_inference",
    }
    assert all("fictional" in scenario["description"].lower() for scenario in DEMO_SCENARIOS)


def test_demo_scenarios_include_commercial_sizing_inputs() -> None:
    required = {
        "model_family",
        "model_parameters_billions",
        "precision",
        "region",
        "target_utilization_pct",
        "growth_pct",
        "assumption_overrides",
    }

    for scenario in DEMO_SCENARIOS:
        assert required <= scenario["inputs"].keys()
        assert scenario["name"]
        assert scenario["inputs"]["region"].startswith("fictional-")
