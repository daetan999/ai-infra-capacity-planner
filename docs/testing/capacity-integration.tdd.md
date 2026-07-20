# Capacity workflow integration TDD checkpoint

## RED

The integration contract was written before the sizing engine and HTTP application were merged.
Collection fails while `app.engine` and `app.main` are absent from the product branch.

## GREEN target

One fictional scenario must flow from Pydantic validation through the real deterministic engine and
SQLite repository to the Markdown export. The test asserts the product contract rather than a
mocked score: illustrative profile disclosure, capacity and cost ranges, confidence, assumptions,
validation questions, a measurement plan, and commercial framing.

## REFACTOR target

After the component branches merge, normalize field aliases at one boundary and keep the engine's
returned mapping independent from FastAPI and persistence concerns.
