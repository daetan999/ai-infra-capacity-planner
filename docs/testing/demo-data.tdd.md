# Demo data TDD checkpoint

## RED

`PYTHONPATH=. pytest -q -o addopts='' tests/test_demo_data.py` failed during collection because
`app.demo_data` did not exist.

## GREEN

The minimal implementation defines three fictional scenarios covering LLM training, real-time LLM
inference, and RAG inference. Each fixture includes model, demand, data, region, utilization, growth,
and editable assumption inputs.

## REFACTOR

`fresh_demo_scenarios()` returns deep copies so application startup can seed records without
mutating the canonical fixtures across tests or process restarts.
