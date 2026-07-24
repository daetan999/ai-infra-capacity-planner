# AI Infrastructure Capacity Planner

[![CI](https://github.com/daetan999/ai-infra-capacity-planner/actions/workflows/ci.yml/badge.svg)](https://github.com/daetan999/ai-infra-capacity-planner/actions/workflows/ci.yml)

An explainable first-pass planner that turns an AI workload into indicative infrastructure and
commercial ranges. It keeps the assumptions, likely constraint, confidence deductions, and
validation questions beside the estimate so a reviewer can see what must be measured next.

![Industrial capacity-planning workspace showing a fictional real-time inference scenario and its indicative capacity range](docs/assets/capacity-planner-workspace.png)

*A seeded fictional inference workload in the live planning workspace. The input sheet remains
visible beside the resulting capacity envelope so the estimate can be reviewed rather than treated
as a quote.*

This is a portfolio implementation built with fictional scenarios and generic illustrative hardware
profiles. It does not issue a bill of materials, use live supplier pricing, or replace representative
benchmarking and Solutions Engineer review.

## The decision it supports

Early infrastructure discovery often starts before workload evidence is complete. The planner helps
frame whether a training, inference, retrieval, vision, or batch workload is ready for deeper sizing
and which missing measurements block a credible commercial discussion.

For each scenario it:

1. records demand, model, data, service-level, facility, and growth assumptions;
2. calculates deterministic low-to-high ranges for compute, memory, storage, network, rack, power,
   utilization, and monthly compute cost;
3. exposes theoretical, derated, and target-utilization views;
4. identifies a primary bottleneck hypothesis and confidence basis;
5. turns missing evidence into validation questions; and
6. exports the scenario and result as JSON or a Markdown sizing brief.

## Review the trade-offs

![Focused comparison table for three fictional capacity-planning scenarios](docs/assets/capacity-planner-comparison.png)

*The comparison view keeps workload-specific accelerator, cost, power, confidence, and profile
calibration ranges in one review surface. The figures are illustrative and come from the repository's
bundled demo scenarios.*

The application includes three fictional examples: a time-bounded model-training window, a
latency-sensitive real-time assistant, and a private RAG workload with growing document storage.
They are safe to use in demonstrations and contain no customer names, credentials, production
telemetry, proprietary configurations, or supplier quotes.

## Visual system

The interface is an industrial planning desk rather than a generic analytics dashboard:

- **Graphite** grounds the workspace and its calculation panels.
- **Safety orange** marks the active planning path and primary capacity figures.
- **Brass** identifies evidence, utilization, and caution states.
- **Barlow Semi Condensed** carries the operational hierarchy.
- **Azeret Mono** keeps inputs, ranges, status labels, and comparison data visually aligned.

Square geometry, drafting-grid lines, compact labels, and visible source assumptions reinforce that
the output is a working calculation to inspect—not a polished recommendation to accept.

## Calculation boundary

The deterministic engine supports five workload modes:

- LLM training
- LLM inference
- RAG inference
- vision inference
- batch AI or HPC

Generic profiles in [`data/accelerator_profiles.yaml`](data/accelerator_profiles.yaml) define
illustrative memory, throughput, derating, power, and pricing assumptions with calibration
provenance. The engine returns ranges rather than a topology-level design and carries the profile
limitations into both the interface and exports.

See the [calibration method](docs/calibration-method.md) for the evidence-matching procedure and
[assumptions and guardrails](docs/assumptions-and-guardrails.md) for the interpretation boundary.

## Architecture

The project is a small modular monolith:

```text
Browser workspace
      │
      ▼
FastAPI boundary ─────► SQLite scenario repository
      │
      ├───────────────► Deterministic sizing engine
      │                         │
      │                         ▼
      │                Illustrative YAML profiles
      │
      └───────────────► JSON and Markdown exports
```

| Area | Responsibility |
|---|---|
| `app/schemas.py` | Request validation and API contracts |
| `app/engine.py` | Side-effect-free sizing, confidence, and sensitivity policy |
| `app/repository.py` | Local SQLite persistence |
| `app/main.py` | HTTP routes, demo seeding, comparison, and exports |
| `templates/` and `static/` | Responsive browser workspace and interactions |
| `tests/` | Engine, repository, API, workflow, demo-data, and interface contracts |

The full rationale is documented in [Architecture](docs/architecture.md). Interactive OpenAPI
documentation is available at `/docs` while the service is running.

## Run locally

Requirements: Python 3.12 or later.

```bash
git clone https://github.com/daetan999/ai-infra-capacity-planner.git
cd ai-infra-capacity-planner
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. Demo scenarios are seeded by default when the local database is empty.
Set `SEED_DEMO_DATA=false` to start without them. The container path is:

```bash
docker compose up --build
```

Runtime scenarios are stored in a local SQLite database excluded from version control.

## Quality checks

```bash
make lint
node --check static/app.js
make test
docker build -t capacity-planner:test .
```

Pytest is configured with branch coverage and an 80% application-coverage floor. CI runs Ruff,
JavaScript syntax validation, the test suite, and a clean container build.

## Honest limitations

This is a single-user, local-first planning aid. It has no authentication, multi-tenant isolation,
supplier catalog synchronization, live price feeds, benchmark execution, topology validation,
reservation or discount modeling, tax calculation, procurement workflow, or production
observability. Every result must be reviewed against measured workload behavior, supported hardware
and software, the target operating environment, and current commercial terms.

## License

Released under the [MIT License](LICENSE).

[Enterprise AI Infrastructure Portfolio](https://github.com/daetan999/technical_resume)
