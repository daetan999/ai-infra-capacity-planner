---
name: test-driven-feature-development
description: Workflow command scaffold for test-driven-feature-development in ai-infra-capacity-planner.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /test-driven-feature-development

Use this workflow when working on **test-driven-feature-development** in `ai-infra-capacity-planner`.

## Goal

Implements a new feature or contract by first defining or updating a test/spec, then implementing code, and finally updating documentation.

## Common Files

- `tests/test_*.py`
- `docs/testing/*.tdd.md`
- `app/*.py`
- `static/app.js`
- `templates/index.html`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Define or update a test file (tests/test_*.py or docs/testing/*.tdd.md)
- Implement or update feature code (app/*.py, static/app.js, templates/index.html, etc.)
- Update or add documentation (docs/testing/*.tdd.md, docs/assets/*, README.md)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.