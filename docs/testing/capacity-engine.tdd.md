# Capacity engine TDD evidence

## Source and user journeys

No standalone plan file was provided. The journeys were derived from the Capacity Planner product
requirements for this implementation run:

- As a planner, I can size any supported AI workload mode and receive deterministic indicative
  infrastructure and commercial ranges.
- As a reviewer, I can distinguish theoretical, derated, memory-constrained, and
  utilization-adjusted capacity.
- As a commercial lead, I can see the confidence, missing evidence, assumptions, validation
  questions, and PoC measurements behind a range.
- As a solution designer, I can compare batching, quantization, growth, and latency sensitivities.
- As an API consumer, I can submit the persisted API vocabulary and receive the same result as the
  native engine vocabulary.

## RED, GREEN, and refactor checkpoints

### RED: engine contract

- Checkpoint: `09e96c8 test: define capacity engine contract`
- Command: `python3 -m pytest tests/test_engine.py -q -o addopts=''`
- Intended failure: test collection failed with
  `ModuleNotFoundError: No module named 'app.domain'`. The new contract referenced the missing
  domain and engine modules before production code existed.

### RED: API alias contract

- Command:
  `python3 -m pytest tests/test_engine.py::test_api_alias_mapping_matches_canonical_engine_inputs -q -o addopts=''`
- Intended failure: the API-shaped request and native request produced different accelerator
  ranges because the API aliases and nested assumption overrides were not yet normalized.

### GREEN

- Checkpoint: `6e90140 feat: implement deterministic capacity sizing engine`
- Command:
  `PYTHONPATH=work/python_deps/capacity python3 -m pytest tests/test_engine.py --cov=app.domain --cov=app.engine --cov-report=term-missing --cov-fail-under=80 -o addopts=''`
- Result: `17 passed in 0.30s`; total branch-aware coverage `91.41%`.
- The previously failing API alias test separately passed with `1 passed in 0.03s` before the full
  suite was run.

### REFACTOR and static verification

- Command: `work/python_deps/capacity/bin/ruff check app/domain.py app/engine.py tests/test_engine.py`
- Result: `All checks passed!`
- Command: `git diff --check`
- Result: passed with no whitespace errors.
- Refactoring moved boundary normalization into the domain module, kept estimation pure and
  deterministic, and separated range, confidence, assumption, question, PoC, and sensitivity
  composition into focused helpers.

## Test specification

| # | What is guaranteed | Test | Type | Result |
|---|---|---|---|---|
| 1 | Every YAML profile is generic, complete, positive, and explicitly illustrative | `test_profiles_are_vendor_neutral_and_explicitly_illustrative` | Unit | PASS |
| 2 | Identical input mappings produce identical JSON-friendly results | `test_calculation_is_deterministic_and_json_friendly` | Unit | PASS |
| 3 | Persisted API aliases and native engine fields produce identical results | `test_api_alias_mapping_matches_canonical_engine_inputs` | Contract | PASS |
| 4 | All five workload modes return accelerator, CPU, memory, storage, network, rack, power, and monthly-cost ranges | `test_every_workload_mode_returns_complete_indicative_ranges` | Parameterized unit | PASS |
| 5 | Theoretical capacity does not exceed derated or utilization-adjusted capacity | `test_views_show_theoretical_derated_and_utilization_capacity` | Unit | PASS |
| 6 | Higher growth and tighter latency never understate the baseline accelerator minimum | `test_growth_and_latency_sensitivities_never_understate_baseline` | Unit | PASS |
| 7 | Illustrative batching and lower precision expose non-increasing accelerator opportunities | `test_batching_and_quantization_sensitivities_show_efficiency_opportunity` | Unit | PASS |
| 8 | Sparse input reduces confidence and creates explicit validation and measurement work | `test_sparse_inputs_lower_confidence_and_generate_validation_work` | Unit | PASS |
| 9 | Large model state can make accelerator memory the primary bottleneck | `test_memory_floor_can_become_primary_bottleneck` | Unit | PASS |
| 10 | Unsupported mode/profile/precision and invalid numeric values fail with actionable errors | `test_invalid_inputs_fail_with_actionable_messages` | Boundary unit | PASS |

## Coverage and known gaps

The owned domain and engine modules reached `91.41%` branch-aware coverage, exceeding the 80%
gate. The remaining uncovered paths are defensive profile-file and malformed-YAML validation,
several alternative bottleneck/commercial-band branches, and a few field-specific validation
errors. API persistence, browser workflow, and end-to-end export coverage belong to their
respective workstreams.

The formulas use normalized workload units, illustrative derating, and placeholder cost ranges.
They intentionally make no vendor performance or price claims. Representative workload
benchmarks and current commercial inputs remain required before architecture or purchasing
commitments.
