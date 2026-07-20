```markdown
# ai-infra-capacity-planner Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and collaborative workflows used in the `ai-infra-capacity-planner` Python codebase. You'll learn how to contribute features, extend APIs, enhance the UI, update infrastructure, and manage demo data using established step-by-step processes. The repository emphasizes test-driven development, clear commit conventions, and modular code organization.

---

## Coding Conventions

**File Naming**
- Use camelCase for file names.
  - Example: `capacityPlanner.py`, `demoData.py`

**Imports**
- Use relative imports within modules.
  - Example:
    ```python
    from .schemas import CapacitySchema
    from .repository import get_capacity_data
    ```

**Exports**
- Use named exports (explicitly specify what is exported).
  - Example:
    ```python
    __all__ = ["CapacitySchema", "get_capacity_data"]
    ```

**Commit Messages**
- Follow [Conventional Commits](https://www.conventionalcommits.org/) with these prefixes: `test`, `docs`, `feat`, `fix`, `build`, `style`, `ci`.
- Keep commit messages concise (~41 characters on average).
  - Example: `feat: add scenario planner endpoint`

---

## Workflows

### Test-Driven Feature Development

**Trigger:** When adding a new feature or enforcing a contract using TDD  
**Command:** `/new-feature-tdd`

1. Define or update a test file  
   - Example: `tests/test_capacityPlanner.py`
2. Implement or update the feature code  
   - Example: `app/capacityPlanner.py`
3. Update or add documentation  
   - Example: `docs/testing/capacity-planner.tdd.md`

**Example:**
```python
# tests/test_capacityPlanner.py
def test_new_feature():
    result = new_feature()
    assert result == expected_value
```

---

### API or Interface Extension

**Trigger:** When adding or modifying an API endpoint or interface  
**Command:** `/new-api-endpoint`

1. Update or create API implementation  
   - Example: `app/main.py`
2. Update or create schema or repository  
   - Example: `app/schemas.py`, `app/repository.py`
3. Add or update relevant tests  
   - Example: `tests/test_api.py`, `tests/test_repository.py`
4. Document API contract or scenarios  
   - Example: `docs/testing/capacity-api.tdd.md`

**Example:**
```python
# app/main.py
@app.route("/api/capacity", methods=["POST"])
def create_capacity():
    data = request.json
    # implementation...
```

---

### UI Workspace Enhancement

**Trigger:** When adding or improving the web UI or visual assets  
**Command:** `/ui-enhancement`

1. Add or update static JavaScript and CSS  
   - Example: `static/app.js`, `static/styles.css`
2. Modify HTML templates  
   - Example: `templates/index.html`
3. Add or update visual assets  
   - Example: `docs/assets/diagram.png`, `static/favicon.svg`
4. Update documentation or screenshots  
   - Example: `docs/testing/browser-qa.md`

**Example:**
```html
<!-- templates/index.html -->
<script src="/static/app.js"></script>
<link rel="stylesheet" href="/static/styles.css">
```

---

### Infrastructure or CI Update

**Trigger:** When improving build, delivery, or CI/CD configuration  
**Command:** `/ci-update`

1. Modify CI workflow files  
   - Example: `.github/workflows/ci.yml`
2. Update Docker or Compose files  
   - Example: `Dockerfile`, `compose.yaml`, `.dockerignore`
3. Adjust package metadata  
   - Example: `pyproject.toml`, `.gitignore`

**Example:**
```yaml
# .github/workflows/ci.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
```

---

### Demo Data or Scenario Update

**Trigger:** When introducing or modifying demo scenarios for testing or showcasing  
**Command:** `/update-demo-scenario`

1. Add or update demo data files  
   - Example: `app/demo_data.py`
2. Update or add tests for demo data  
   - Example: `tests/test_demo_data.py`
3. Document demo scenarios  
   - Example: `docs/testing/demo-data.tdd.md`

**Example:**
```python
# app/demo_data.py
demo_capacity = [
    {"id": 1, "name": "Test Scenario", "capacity": 100}
]
```

---

## Testing Patterns

- Tests are written in Python, typically in files named `test_*.py` under the `tests/` directory.
- Test-driven development is encouraged: write or update tests before implementing features.
- No specific test framework is enforced, but standard Python testing practices apply.

**Example:**
```python
# tests/test_repository.py
def test_get_capacity_data():
    data = get_capacity_data()
    assert isinstance(data, list)
```

---

## Commands

| Command              | Purpose                                                         |
|----------------------|-----------------------------------------------------------------|
| /new-feature-tdd     | Start a test-driven feature development workflow                |
| /new-api-endpoint    | Add or extend an API endpoint or interface contract             |
| /ui-enhancement      | Enhance or update the UI workspace and visual assets            |
| /ci-update           | Update infrastructure, CI/CD workflows, or package metadata     |
| /update-demo-scenario| Add or update demo data and related tests for new scenarios     |
```
