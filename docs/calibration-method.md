# Calibration Method

The planner starts with normalized, illustrative profiles. Calibration replaces one planning
assumption with reproducible evidence; it does not convert a public benchmark into a customer
quote or final design.

## Evidence required

A benchmark can anchor a profile only when the following fields are comparable:

| Area | Match required before reuse |
|---|---|
| Workload | model architecture and size, task, quality target, input and output distribution |
| Runtime | precision, quantization, serving framework, batching, parallelism, and software version |
| Service target | scenario, concurrency, throughput metric, latency definition, and percentile |
| System | accelerator model and count, memory, CPU, interconnect, storage, and power configuration |
| Operations | availability posture, utilization target, growth headroom, and failure-domain design |
| Commercial | region, term, support, reservation or discount basis, and price source |

If a material field does not match, keep `calibration_status: illustrative` and record the mismatch.

## Procedure

1. Freeze the customer workload definition and success criteria.
2. Select a result for the same task and deployment scenario.
3. Record the complete system-under-test configuration and benchmark software.
4. Confirm that the published accuracy and latency constraints meet the customer requirement.
5. Normalize the measured result to a per-system value without assuming linear scale-out.
6. Replay a representative workload on supported target hardware.
7. Replace the planning throughput only after the replay meets quality, latency, reliability, and
   observability gates.
8. Obtain current commercial terms separately. Performance evidence does not establish price.

MLCommons documents separate Server, Interactive, and Offline scenarios, and its LoadGen harness
controls query scheduling, latency tracking, accuracy validation, and final metric calculation. The
Closed division exists for comparable reference setups. These controls explain why the scenario and
system description must travel with any result.

Primary sources:

- [MLPerf Inference benchmark definitions](https://docs.mlcommons.org/inference/)
- [MLPerf Inference submission guide](https://docs.mlcommons.org/inference/submission/)
- [MLPerf Inference v5.1 results](https://docs.mlcommons.org/inference_results_v5.1/)

## Worked comparability check

Consider the bundled 70B inference planning scenario. It assumes an 8,192-token context, 1,200
average input tokens, 300 average output tokens, an 800 ms end-to-end target, and a generic serving
profile.

The MLPerf Llama 2 70B definition uses OpenORCA with a maximum sequence length of 1,024 and evaluates
time to first token and time per output token under its defined scenarios. Published v5.1 results
also identify the full submitted system and accelerator count.

| Check | Portfolio scenario | Public benchmark | Decision |
|---|---|---|---|
| Model class | 70B generic decoder | Llama 2 70B | Partial match |
| Sequence profile | up to 8,192 context; 1,500 average total tokens | OpenORCA, maximum sequence length 1,024 | Mismatch |
| Latency target | 800 ms end to end | separate TTFT and TPOT constraints | Mismatch |
| Serving stack | unspecified until discovery | submission-specific | Unknown |
| Hardware topology | generic illustrative profile | submission-specific system | Mismatch |
| Accuracy target | customer acceptance criteria required | MLPerf reference accuracy rules | Unknown |

The result fails the comparability gate. The planner must not copy the published throughput into the
bundled profile. A Solutions Engineer can use the benchmark to design the replay and identify the
required system metadata, then calibrate with the representative workload.

## Status contract

- `illustrative`: normalized planning values with no workload-comparable benchmark applied.
- `benchmark_anchored`: a named public or customer-approved measurement matches the documented
  scope closely enough to anchor one or more profile fields. Customer replay and commercial review
  remain required.

Every bundled profile remains `illustrative`.
