import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"
SCRIPT = ROOT / "static" / "app.js"
STYLES = ROOT / "static" / "styles.css"
ASSETS = ROOT / "docs" / "assets"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_workspace_exposes_the_complete_planning_journey() -> None:
    html = read(TEMPLATE)

    assert '<html lang="en">' in html
    assert 'href="#main-content"' in html
    for landmark in (
        'id="scenario-form"',
        'id="workload-mode"',
        'id="assumption-editor"',
        'id="results-panel"',
        'id="comparison-panel"',
        'id="validation-questions"',
    ):
        assert landmark in html

    for workload in (
        "LLM training",
        "LLM inference",
        "RAG inference",
        "Vision inference",
        "Batch AI / HPC",
    ):
        assert workload in html


def test_form_controls_are_labeled_and_cover_material_inputs() -> None:
    html = read(TEMPLATE)
    expected_controls = {
        "scenario-name",
        "model-family",
        "model-parameters",
        "precision",
        "context-length",
        "tokens-per-request",
        "average-input-tokens",
        "average-output-tokens",
        "tokens-per-day",
        "requests-per-second",
        "concurrency",
        "peak-factor",
        "latency-target",
        "availability-target",
        "dataset-size",
        "training-window",
        "storage-required",
        "monthly-growth",
        "demand-growth",
        "ingress",
        "egress",
        "region",
        "target-utilization",
    }

    for control_id in expected_controls:
        assert f'id="{control_id}"' in html
        assert re.search(rf'<label[^>]+for="{control_id}"', html)


def test_form_payload_uses_canonical_capacity_input_keys() -> None:
    html = read(TEMPLATE)
    script = read(SCRIPT)
    canonical_keys = {
        "model_parameters_billions",
        "model_family",
        "context_tokens",
        "average_input_tokens",
        "average_output_tokens",
        "tokens_per_day",
        "dataset_tb",
        "storage_tb",
        "storage_growth_pct",
        "growth_pct",
    }

    for key in canonical_keys:
        assert f'name="{key}"' in html
        assert f'"{key}"' in script

    for profile_id in (
        "illustrative-efficient",
        "illustrative-balanced",
        "illustrative-memory-dense",
    ):
        assert f'value="{profile_id}"' in html
    assert 'value="fp8"' not in html


def test_results_make_estimates_and_uncertainty_visible() -> None:
    html = read(TEMPLATE)
    for result in (
        "Accelerators",
        "CPU cores",
        "Memory",
        "Storage",
        "Network",
        "Racks",
        "Power",
        "Monthly cost",
        "Theoretical",
        "Derated",
        "Utilization",
        "Bottleneck",
        "Confidence",
        "Missing inputs",
    ):
        assert result in html

    assert "Indicative range" in html
    assert "not a final vendor quote" in html
    assert "Requires benchmark validation" in html


def test_interactive_states_exports_and_comparison_have_accessible_hooks() -> None:
    html = read(TEMPLATE)
    script = read(SCRIPT)

    for state in ("empty-state", "loading-state", "success-state", "error-state"):
        assert f'id="{state}"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-live="assertive"' in html
    assert 'id="export-json"' in html
    assert 'id="export-markdown"' in html
    assert 'id="compare-scenarios"' in html

    for endpoint in (
        "/api/scenarios",
        "/api/scenarios/compare",
        "/export?format=json",
        "/export?format=markdown",
    ):
        assert endpoint in script

    assert "textContent" in script
    assert "innerHTML" not in script
    assert "setRequestState" in script
    assert "AbortController" in script
    assert "Number(input.value)" in script
    assert 'id="comparison-head"' in html


def test_renderer_understands_the_engine_result_contract() -> None:
    script = read(SCRIPT)

    for engine_key in (
        "result.capacity",
        "capacity.monthly_cost_usd",
        "views.theoretical_accelerators",
        "views.derated_accelerators",
        "views.target_utilization_pct",
        "confidence.missing_inputs",
        "commercial_band.monthly_range_usd",
    ):
        assert engine_key in script


def test_layout_supports_keyboard_mobile_and_reduced_motion() -> None:
    styles = read(STYLES)

    assert ":focus-visible" in styles
    assert "@media (max-width: 760px)" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles
    assert ".skip-link" in styles
    assert "minmax(0, 1fr)" in styles


def test_original_diagrams_have_accessible_metadata_and_real_content() -> None:
    expected = {
        "capacity-planner-hero.svg": ("Capacity planning control plane", 12),
        "sizing-workflow.svg": ("Sizing workflow", 10),
        "sizing-model.svg": ("Capacity sizing model", 10),
    }

    for name, (title, minimum_shapes) in expected.items():
        svg = read(ASSETS / name)
        assert "<svg" in svg and "viewBox=" in svg
        assert f"<title>{title}</title>" in svg
        assert "<desc>" in svg
        shape_count = sum(svg.count(f"<{tag}") for tag in ("rect", "path", "circle", "line"))
        assert shape_count >= minimum_shapes
