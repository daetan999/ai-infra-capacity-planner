# Capacity workflow integration TDD checkpoint

## RED

The integration contract was written before the sizing engine and HTTP application were merged.
Collection fails while `app.engine` and `app.main` are absent from the product branch.

## GREEN

One fictional scenario now flows from Pydantic validation through the real deterministic engine and
SQLite repository to the Markdown export. The test asserts the product contract rather than a
mocked score: illustrative profile disclosure, capacity and cost ranges, confidence, assumptions,
validation questions, a measurement plan, and commercial framing.

`PYTHONPATH=. pytest` completed with 58 passing tests and 92.72% branch-aware application coverage.

## REFACTOR

Field aliases are normalized at the domain boundary, the API passes a plain mapping to the engine,
and the engine returns a JSON-friendly mapping independent from FastAPI and SQLite. Integration
review also added coverage for zero-valued non-applicable fields, strict training windows, blank
evidence, runnable demo profiles, seeded fixture idempotency, and numeric comparison identifiers.
