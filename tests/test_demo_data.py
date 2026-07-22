from app.demo_data import DEMO_SCENARIOS, fresh_demo_scenarios
from app.engine import calculate_capacity


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


def test_every_demo_scenario_produces_a_runnable_indicative_range() -> None:
    for scenario in fresh_demo_scenarios():
        result = calculate_capacity(
            {"workload_mode": scenario["workload_mode"], **scenario["inputs"]}
        )

        assert result["profile"]["illustrative"] is True
        assert result["capacity"]["accelerators"]["min"] > 0
        assert "not a vendor quote" in result["commercial_band"]["caveat"].lower()


def test_northstar_demo_matches_the_portfolio_case_contract() -> None:
    northstar = next(
        scenario for scenario in DEMO_SCENARIOS if "Northstar" in scenario["name"]
    )

    assert northstar["name"] == "Fictional Northstar Private RAG"
    assert northstar["workload_mode"] == "rag_inference"
    assert northstar["inputs"]["model_parameters_billions"] == 70
    assert northstar["inputs"]["requests_per_second"] == 45
    assert northstar["inputs"]["peak_factor"] == 1.0
    assert northstar["inputs"]["latency_target_ms"] == 900
    assert northstar["inputs"]["dataset_tb"] == 18
    assert northstar["inputs"]["growth_pct"] == 35
