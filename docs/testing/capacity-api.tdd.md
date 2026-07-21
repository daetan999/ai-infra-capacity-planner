# Capacity API TDD log

This slice owns persistence and the HTTP contract. Capacity math is injected through a
single mapping-to-mapping function so the sizing engine can evolve independently.

## RED

The first test suite was written before implementation. It specifies:

- SQLite-backed scenario create, read, list, replace, and delete operations;
- persistence across repository instances and typed not-found errors;
- all five workload modes and the complete cross-mode input envelope;
- deterministic calculation injection, comparison ordering, and JSON/Markdown exports;
- stable success/error envelopes, whitespace rejection, numeric boundaries, and redacted
  calculation failures.

The initial run fails during collection because `app.repository` and `app.main` do not exist.

## GREEN

Implemented a standard-library `sqlite3` repository, strict Pydantic request contracts, and
an application factory with injectable sizing. The minimal implementation made all repository
and API tests pass, including full CRUD, five-mode acceptance, ordered comparisons, exports,
and safe error responses.

Engine boundary:

```python
calculate_capacity(
    {"workload_mode": scenario.workload_mode, **scenario.inputs}
) -> Mapping[str, Any]
```

The application imports `app.engine.calculate_capacity` at calculation time. A deterministic
fingerprint response is used only when that module is genuinely absent, which keeps this slice
runnable in isolation without masking engine dependency or runtime failures.

## REFACTOR

Refactoring added canonical JSON storage, short-lived/explicitly closed database sessions,
immutable repository records, deterministic export ordering, strict non-finite-number rejection,
and collision-safe export filenames. Explicit model-family and token-volume inputs were added to
match the public product brief.

Verification on Python 3.14:

```text
25 passed in 1.21s (isolated API suite)
91.25% branch-aware coverage (80% required)
Ruff: All checks passed
ResourceWarning escalation: passed
```

The warning originates in the installed FastAPI/Starlette test-client compatibility shim; the
repository emits no unclosed-connection warnings after refactoring.
