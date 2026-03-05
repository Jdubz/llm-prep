# 01 – pytest Fixtures and Basics

## Prerequisites

You should be comfortable with Python basics and have written at least a few modules.
If you've done extensive testing in Vitest/Jest, most concepts transfer — but Python's testing
ecosystem has different idioms worth internalizing.

---

## The Mental Model Shift from Vitest/Jest

In Vitest/Jest, you think in `describe` blocks, `beforeEach`/`afterEach`, and `it` functions.
In pytest, the primary abstraction is the **fixture** — a composable, dependency-injected setup
function that replaces `beforeEach`, factories, and mocking setup all at once.

```python
import pytest

@pytest.fixture
def db():
    """This IS your beforeEach. Cleanup goes after yield."""
    database = create_test_db()
    yield database          # <-- test runs here
    database.cleanup()      # <-- this is your afterEach

def test_creates_user(db):  # <-- db is injected automatically by name
    user = db.create_user(name="Alice")
    assert user.name == "Alice"
```

### pytest vs Vitest Quick Reference

| Vitest / Jest | pytest | Notes |
|---|---|---|
| `describe("group", () => {})` | `class TestGroup:` or group by file | Classes optional |
| `it("does X", () => {})` | `def test_does_x():` | Must start with `test_` |
| `expect(x).toBe(y)` | `assert x == y` | Plain assert; pytest rewrites for diffs |
| `expect(x).toEqual(y)` | `assert x == y` | Python `==` does deep comparison |
| `expect(fn).toThrow()` | `with pytest.raises(Error):` | Context manager |
| `beforeEach(() => {})` | `@pytest.fixture` | Injected by argument name |
| `afterEach(() => {})` | `yield` inside fixture | Code after yield is teardown |
| `beforeAll()` | `@pytest.fixture(scope="session")` | Session/module/class scope |
| `jest.mock("module")` | `monkeypatch` or `mock.patch` | Multiple approaches |
| `jest.fn()` | `MagicMock()` / `AsyncMock()` | From `unittest.mock` |
| `test.each([...])` | `@pytest.mark.parametrize` | More flexible |
| `vitest --coverage` | `pytest --cov=app` | Requires `pytest-cov` |

---

## Fixtures in Depth

```python
# Function scope (default) — once per test
@pytest.fixture
def user():
    return User(name="Test User", email="test@example.com")

# Session scope — once for entire test suite
@pytest.fixture(scope="session")
def database_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

# Fixtures depend on other fixtures (composable DI)
@pytest.fixture
def authenticated_client(api_client, user):
    token = create_token(user)
    api_client.headers["Authorization"] = f"Bearer {token}"
    return api_client

# Autouse — applies to every test without being requested
@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
```

---

## Parametrize — Data-Driven Tests

```python
@pytest.mark.parametrize("email,is_valid", [
    ("user@example.com", True),
    ("user@.com", False),
    ("", False),
    ("user+tag@example.com", True),
])
def test_email_validation(email: str, is_valid: bool):
    assert validate_email(email) == is_valid

# With IDs for readable output
@pytest.mark.parametrize("status_code,expected", [
    pytest.param(200, {"status": "ok"}, id="success"),
    pytest.param(404, {"detail": "Not found"}, id="not-found"),
])
def test_error_responses(status_code, expected): ...
```

---

## Markers

```python
@pytest.mark.slow
def test_large_dataset(): ...

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature(): ...

@pytest.mark.xfail(reason="Known bug #123")
def test_known_broken(): ...

# Run: pytest -m "not slow"
```

---

## conftest.py — Shared Fixtures

`conftest.py` is pytest's mechanism for sharing fixtures across test files.

```
tests/
    conftest.py          # Available to ALL tests
    test_users.py
    api/
        conftest.py      # Available to tests in api/
        test_endpoints.py
```

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def db_session():
    async with AsyncSession(engine) as session:
        async with session.begin():
            yield session
            await session.rollback()
```

---

## Async Testing with pytest-asyncio

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

```python
# With asyncio_mode = "auto", just write async test functions
async def test_async_database_query(db_session):
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    await db_session.flush()
    result = await db_session.execute(select(User).where(User.email == "alice@example.com"))
    assert result.scalar_one().name == "Alice"
```

---

## Mocking with monkeypatch and unittest.mock

```python
# monkeypatch — replace attributes/env vars for a test
def test_with_monkeypatch(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setattr("mymodule.external_api", lambda: {"mock": True})
    result = my_function()
    assert result["mock"] is True

# unittest.mock — more flexible mocking
from unittest.mock import MagicMock, AsyncMock, patch

def test_with_mock():
    service = MagicMock()
    service.get_user.return_value = {"name": "Alice"}
    result = service.get_user(1)
    service.get_user.assert_called_once_with(1)

async def test_async_mock():
    service = AsyncMock()
    service.fetch.return_value = {"data": 42}
    result = await service.fetch("key")
    assert result["data"] == 42
```

---

## Type Checking with mypy

```toml
[tool.mypy]
python_version = "3.12"
strict = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

---

## Linting with Ruff

Ruff replaces flake8, isort, black, and more. Written in Rust, extremely fast.

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "ASYNC", "S", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

```bash
ruff check app/ --fix && ruff format app/
```

---

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: detect-private-key
```

---

## Quick Commands

```bash
pytest                              # Run all
pytest --cov=app --cov-report=term  # With coverage
pytest tests/test_users.py          # Specific file
pytest -m "not slow"                # By marker
pytest -x --tb=short               # Fail fast, short traceback
pytest --durations=10               # Find slow tests
pytest -n auto                      # Parallel (pytest-xdist)
mypy app/ --strict                  # Type check
ruff check app/ --fix && ruff format app/  # Lint + format
```

---

## Key Takeaways

- Fixtures are composable, dependency-injected, and replace `beforeEach`/`afterEach` with a single function.
- `yield` in a fixture unifies setup and teardown; code after `yield` is guaranteed to run.
- `scope="session"` runs a fixture once for all tests; use for expensive setup like database engines.
- `asyncio_mode = "auto"` in pyproject.toml lets you write `async def test_*` without decorators.
- `conftest.py` shares fixtures across test files; nest them to scope fixtures by directory.
