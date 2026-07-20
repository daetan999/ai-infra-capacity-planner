# Capacity Planner interface TDD evidence

## Source and journeys

The journeys were derived from the Capacity Planner portfolio specification and the interface ownership brief; no separate plan file was used.

- As an infrastructure planner, I can describe a workload and edit sizing assumptions so that I can create an auditable first-pass scenario.
- As a commercial or technical reviewer, I can see capacity ranges, the throughput bridge, uncertainty, and missing evidence before treating an estimate as a commitment.
- As a decision team, we can compare two or three saved scenarios and export a machine-readable record or a Markdown brief.
- As a keyboard, mobile, or motion-sensitive user, I can navigate the same workflow without losing content or status feedback.

## RED → GREEN → REFACTOR

| Stage | Commit | Command | Evidence |
|---|---|---|---|
| RED | `f9102ce` | `python3 -m pytest tests/test_interface_contract.py -q -o addopts=''` | Six tests failed because the owned template, script, stylesheet, and diagrams did not exist. The failures were on the intended interface boundary. |
| GREEN | `72575ca` | `python3 -m pytest tests/test_interface_contract.py -q -o addopts=''` | `6 passed`; the same tests now validate the complete workspace contract. |
| RED (integration mapping) | `a83f83a` | `python3 -m pytest tests/test_interface_contract.py::test_renderer_understands_the_engine_result_contract -q -o addopts=''` | The new test failed because the renderer did not yet map the engine's nested capacity, views, confidence, and commercial-band objects. |
| RED (canonical inputs) | `56bb079` | `python3 -m pytest tests/test_interface_contract.py::test_form_payload_uses_canonical_capacity_input_keys -q -o addopts=''` | The new test failed against stale field names and placeholder profile IDs before the form was aligned to the strict API schema and profile YAML. |
| GREEN / REFACTOR | current evidence commit | `node --check static/app.js` and the full interface test command above | `8 passed`; mapped the finalized engine contract, aligned canonical form keys and profile IDs, removed the external font dependency, improved API error-envelope handling, and retained a valid script. |

## Test specification

| # | What is guaranteed | Test target | Type | Result |
|---|---|---|---|---|
| 1 | The page exposes scenario creation, five workload modes, assumption editing, results, comparison, questions, and export actions. | `test_workspace_exposes_the_complete_planning_journey` | Interface contract | PASS |
| 2 | Material compute, service, data, network, regional, and utilization fields have explicit labels. | `test_form_controls_are_labeled_and_cover_material_inputs` | Accessibility contract | PASS |
| 3 | Results expose all requested infrastructure and commercial measures plus theoretical, derated, utilization, bottleneck, confidence, and missing-input signals. | `test_results_make_estimates_and_uncertainty_visible` | Content contract | PASS |
| 4 | Empty, loading, success, and error states are announced; comparison and both exports use the agreed API paths; dynamic content uses safe DOM text assignment. | `test_interactive_states_exports_and_comparison_have_accessible_hooks` | Interaction/security contract | PASS |
| 5 | Focus visibility, mobile reflow, skip navigation, and reduced-motion preferences have explicit styling. | `test_layout_supports_keyboard_mobile_and_reduced_motion` | Responsive/accessibility contract | PASS |
| 6 | All three required SVG diagrams contain accessible metadata and substantive original geometry. | `test_original_diagrams_have_accessible_metadata_and_real_content` | Asset contract | PASS |
| 7 | The renderer directly understands the sizing engine's nested capacity, throughput-view, confidence, and commercial-band structures. | `test_renderer_understands_the_engine_result_contract` | Integration contract | PASS |
| 8 | The submitted form uses only canonical API keys, supported precisions, and the exact illustrative profile identifiers from YAML. | `test_form_payload_uses_canonical_capacity_input_keys` | API contract | PASS |

## API contract

The client accepts direct payloads or the repository's `{success, data, error}` envelope.

- `GET /api/scenarios` returns the scenario collection.
- `POST /api/scenarios` accepts `{name, workload_mode, inputs}`. Assumption overrides are nested at `inputs.assumption_overrides`; the selected accelerator profile is `inputs.accelerator_profile`.
- `POST /api/scenarios/compare` accepts `{scenario_ids: [...]}`.
- `GET /api/scenarios/{id}/export?format=json|markdown` returns a downloadable raw attachment.

## Coverage and known gaps

This owned slice has eight passing static interface contract tests and a passing JavaScript syntax check. Application-level coverage is measured by the integrated repository suite because these static assets do not add Python statements. Browser-level validation against the live FastAPI service remains an integration task after the API and sizing engine branches are combined; that run should exercise create, compare, failure recovery, exports, keyboard focus, and a narrow viewport.
