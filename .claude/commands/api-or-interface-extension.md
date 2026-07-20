---
name: api-or-interface-extension
description: Workflow command scaffold for api-or-interface-extension in ai-infra-capacity-planner.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /api-or-interface-extension

Use this workflow when working on **api-or-interface-extension** in `ai-infra-capacity-planner`.

## Goal

Adds or extends an API endpoint or interface contract, including implementation, schema, repository, and test updates.

## Common Files

- `app/main.py`
- `app/schemas.py`
- `app/repository.py`
- `tests/test_api.py`
- `tests/test_repository.py`
- `docs/testing/capacity-api.tdd.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Update or create API implementation (app/main.py)
- Update or create schema or repository (app/schemas.py, app/repository.py)
- Add or update relevant tests (tests/test_api.py, tests/test_repository.py)
- Document API contract or scenarios (docs/testing/capacity-api.tdd.md)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.