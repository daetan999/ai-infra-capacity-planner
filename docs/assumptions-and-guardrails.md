# Assumptions and guardrails

This planner supports discovery and first-pass commercial conversations. It does not produce a
final vendor quote, promise benchmark performance, or replace a solution engineering review.

## Interpretation

- Hardware and price profiles are fictional, illustrative planning inputs.
- Ranges communicate uncertainty; the base value is not a commitment.
- Theoretical throughput is reduced by profile derating and the scenario's target utilization.
- Monthly cost is an indicative planning band derived from an illustrative hourly source type.
- Missing evidence lowers confidence and becomes an explicit validation question.
- Peak traffic, latency objectives, availability, data growth, and network movement can each become
  the binding constraint even when raw compute looks sufficient.

## Before commercial validation

Confirm the actual model build, serving stack, sequence-length distribution, batch behavior,
precision support, observed tokens or samples per second, regional availability, resiliency design,
storage class, data locality, ingress/egress terms, and current supplier pricing. Re-run the planner
with measured values and record the benchmark date and environment.

See [Calibration Method](calibration-method.md) for the evidence-matching procedure and a worked
example that remains illustrative because the public benchmark does not match the scenario.

## Safe demo data

Bundled scenarios are fictional. They contain no customer names, credentials, proprietary pricing,
or production telemetry.
